import os
import re
import time
from typing import Any, cast

import jenkins
from simple_logger.logger import get_logger


# Default error patterns for build log analysis.
# Dictionary order determines priority: earlier categories match first.
# Each line is matched against categories in order; first match wins.
DEFAULT_ERROR_PATTERNS: dict[str, list[str]] = {
    "error": [
        r"(?i)\berror\b",
        r"\[ERROR\]",
    ],
    "exception": [
        r"(?i)\bexception\b",
        r"(?i)traceback \(most recent call last\)",
        r"(?i)^\s+at\s+[\w.$]+\([\w.]+:\d+\)",  # Java stack trace lines
    ],
    "failure": [
        r"(?i)\bfailed\b",
        r"(?i)\bfailure\b",
    ],
    "jenkins": [
        r"Build step '.+' marked build as failure",
        r"Finished: FAILURE",
        r"Finished: ABORTED",
        r"(?i)fatal:",
    ],
}


class JenkinsApiError(Exception):
    """Base exception for Jenkins API errors."""

    pass


class JenkinsConnectionError(JenkinsApiError):
    """Raised when connection to Jenkins server fails."""

    pass


class JenkinsJobNotFoundError(JenkinsApiError):
    """Raised when a Jenkins job is not found."""

    pass


class JenkinsJobExecutionError(JenkinsApiError):
    """Raised when job execution fails."""

    pass


class JenkinsBuildNotFoundError(JenkinsApiError):
    """Raised when a build is not found."""

    pass


class JenkinsApi(jenkins.Jenkins):
    def __init__(self) -> None:
        os.environ["PYTHONHTTPSVERIFY"] = "0"

        # Get credentials from environment variables
        server = os.getenv("JENKINS_URL")
        username = os.getenv("JENKINS_USERNAME")
        password = os.getenv("JENKINS_PASSWORD")

        if not server or not username or not password:
            raise ValueError(
                "Missing Jenkins credentials. Please set JENKINS_URL, JENKINS_USERNAME, and JENKINS_PASSWORD environment variables."
            )

        self.logger = get_logger(__name__)
        self.logger.info(f"Connecting to Jenkins server: {server}")

        super(JenkinsApi, self).__init__(
            url=server,
            username=username,
            password=password,
        )

    def get_job_details(self, job_name: str) -> dict[str, Any]:
        """
        Get job information (everything except console output).

        Args:
            job_name: Name of the Jenkins job

        Returns:
            dict: Job information

        Raises:
            JenkinsJobNotFoundError: If the job is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info(f"Getting job info for: {job_name}")
            job_info = self.get_job_info(job_name)
            self.logger.info(f"Successfully retrieved job info for: {job_name}")
            return job_info
        except jenkins.JenkinsException as e:
            error_msg = f"Jenkins error getting job info for '{job_name}': {str(e)}"
            self.logger.error(error_msg)

            # Check for specific error types
            if "does not exist" in str(e).lower():
                raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
            elif "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise JenkinsConnectionError(f"Connection error while getting job '{job_name}': {str(e)}") from e
            else:
                raise JenkinsApiError(f"Jenkins error getting job info for '{job_name}': {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error getting job info for '{job_name}': {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(f"Unexpected error getting job info for '{job_name}': {str(e)}") from e

    def run_job(self, job_name: str, parameters: dict[str, Any] | None = None) -> str:
        """
        Run a job with optional parameters.

        Args:
            job_name: Name of the Jenkins job
            parameters: Optional parameters to pass to the job

        Returns:
            str: Success message with build number or error message
        """
        try:
            self.logger.info(f"Running job: {job_name} with parameters: {parameters}")

            if parameters:
                self.build_job(job_name, parameters)
            else:
                self.build_job(job_name)

            # Get the next build number
            next_build_number = self.get_job_info(job_name)["nextBuildNumber"]
            success_msg = f"Job '{job_name}' started successfully. Build number: {next_build_number - 1}"
            self.logger.info(success_msg)
            return success_msg
        except jenkins.JenkinsException as e:
            error_msg = f"Jenkins error running job '{job_name}': {str(e)}"
            self.logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error running job '{job_name}': {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    def get_job_console(
        self,
        job_name: str,
        build_number: int | None = None,
        tail: int | None = None,
        head: int | None = None,
    ) -> str:
        """
        Get console output for a job build.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number (uses latest if not provided)
            tail: Return only the last N lines of output (mutually exclusive with head)
            head: Return only the first N lines of output (mutually exclusive with tail)

        Returns:
            str: Console output or error message

        Raises:
            ValueError: If both tail and head are provided, or if values are not positive
        """
        # Validate mutually exclusive parameters
        if tail is not None and head is not None:
            raise ValueError("tail and head are mutually exclusive; provide only one")

        # Validate positive values
        if tail is not None and tail <= 0:
            raise ValueError("tail must be a positive integer")
        if head is not None and head <= 0:
            raise ValueError("head must be a positive integer")

        try:
            if build_number is None:
                # Get latest build number
                job_info = self.get_job_info(job_name)
                if job_info.get("lastBuild"):
                    build_number = job_info["lastBuild"]["number"]
                else:
                    error_msg = f"No builds found for job '{job_name}'"
                    self.logger.error(error_msg)
                    return error_msg

            # At this point build_number is guaranteed to be an int
            assert build_number is not None, "build_number should not be None at this point"
            self.logger.info(f"Getting console output for job: {job_name}, build: {build_number}")
            console_output = self.get_build_console_output(job_name, build_number)

            # Apply tail/head filtering
            if tail is not None or head is not None:
                lines = console_output.splitlines()
                if tail is not None:
                    lines = lines[-tail:]
                elif head is not None:
                    lines = lines[:head]
                console_output = "\n".join(lines)

            self.logger.info(f"Successfully retrieved console output for: {job_name}#{build_number}")
            return console_output
        except jenkins.JenkinsException as e:
            error_msg = f"Jenkins error getting console output for '{job_name}#{build_number}': {str(e)}"
            self.logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error getting console output for '{job_name}#{build_number}': {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    def get_all_jobs_list(self) -> list[dict[str, Any]]:
        """
        Get a list of all Jenkins jobs.

        Returns:
            list: List of job information dictionaries

        Raises:
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info("Getting list of all jobs")
            jobs = self.get_all_jobs()
            self.logger.info(f"Successfully retrieved {len(jobs)} jobs")
            return cast(list[dict[str, Any]], jobs)
        except jenkins.JenkinsException as e:
            error_msg = f"Jenkins error getting jobs list: {str(e)}"
            self.logger.error(error_msg)

            # Check for specific error types
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise JenkinsConnectionError(f"Connection error while getting jobs list: {str(e)}") from e
            elif "permission" in str(e).lower():
                raise JenkinsApiError(f"Permission error getting jobs list: {str(e)}") from e
            else:
                raise JenkinsApiError(f"Jenkins error getting jobs list: {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error getting jobs list: {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(f"Unexpected error getting jobs list: {str(e)}") from e

    def wait_for_build(
        self,
        job_name: str,
        build_number: int | None = None,
        timeout: int = 3600,
        poll_interval: int = 30,
    ) -> dict[str, Any]:
        """
        Wait for a Jenkins build to complete.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number to wait for (uses last build if not provided)
            timeout: Maximum wait time in seconds (default: 3600)
            poll_interval: Seconds between status checks (default: 30)

        Returns:
            dict: Build result containing build_number, result, duration, and url

        Raises:
            ValueError: If timeout or poll_interval is not positive
            JenkinsBuildNotFoundError: If the build is not found
            JenkinsJobNotFoundError: If the job is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For timeout or other Jenkins-related errors
        """
        # Validate input parameters
        if timeout <= 0:
            raise ValueError("timeout must be positive (> 0)")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive (> 0)")
        # Adjust poll_interval if it exceeds timeout to allow at least one check
        if poll_interval > timeout:
            poll_interval = timeout

        try:
            # Get build number if not provided
            if build_number is None:
                job_info = self.get_job_info(job_name)
                if job_info.get("lastBuild"):
                    build_number = job_info["lastBuild"]["number"]
                else:
                    raise JenkinsBuildNotFoundError(f"No builds found for job '{job_name}'")

            # At this point build_number is guaranteed to be an int
            assert build_number is not None

            self.logger.info(
                f"Waiting for build: {job_name}#{build_number} (timeout: {timeout}s, poll: {poll_interval}s)"
            )

            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise JenkinsApiError(
                        f"Timeout waiting for build '{job_name}#{build_number}' after {timeout} seconds"
                    )

                try:
                    build_info = self.get_build_info(job_name, build_number)
                except jenkins.JenkinsException as e:
                    if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                        raise JenkinsBuildNotFoundError(f"Build '{job_name}#{build_number}' not found") from e
                    raise

                result = build_info.get("result")
                if result is not None:
                    # Build is complete
                    duration = build_info.get("duration", 0)
                    url = build_info.get("url", "")
                    self.logger.info(f"Build '{job_name}#{build_number}' completed with result: {result}")
                    return {
                        "build_number": build_number,
                        "result": result,
                        "duration": duration,
                        "url": url,
                    }

                # Build still in progress
                self.logger.info(f"Build '{job_name}#{build_number}' still running, waiting {poll_interval}s...")
                time.sleep(poll_interval)

        except JenkinsBuildNotFoundError:
            raise
        except JenkinsApiError:
            raise
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            if "does not exist" in error_msg:
                raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
            elif "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(
                    f"Connection error while waiting for build '{job_name}#{build_number}': {str(e)}"
                ) from e
            else:
                raise JenkinsApiError(f"Jenkins error waiting for build '{job_name}#{build_number}': {str(e)}") from e
        except Exception as e:
            raise JenkinsApiError(f"Unexpected error waiting for build '{job_name}#{build_number}': {str(e)}") from e

    def get_build_errors(
        self,
        job_name: str,
        build_number: int | None = None,
        patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Extract errors from build console output.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number (uses latest if not provided)
            patterns: Custom regex patterns to match (uses default patterns if not provided)

        Returns:
            dict: Contains 'errors' (list of error dicts with line_number, line, category)
                  and 'summary' (count by category)

        Raises:
            JenkinsJobNotFoundError: If the job is not found
            JenkinsBuildNotFoundError: If the build is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info(f"Getting build errors for job: {job_name}, build: {build_number}")

            # Get console output
            console_output = self.get_job_console(job_name, build_number)

            # Check if get_job_console returned an error message
            if console_output.startswith("No builds found for job"):
                raise JenkinsBuildNotFoundError(console_output)
            if "Jenkins error" in console_output or "Unexpected error" in console_output:
                raise JenkinsApiError(console_output)

            # Build pattern dict: either custom patterns or default patterns
            if patterns:
                # Custom patterns go into a single 'custom' category
                pattern_dict: dict[str, list[str]] = {"custom": patterns}
            else:
                pattern_dict = DEFAULT_ERROR_PATTERNS

            # Compile all patterns
            compiled_patterns: dict[str, list[re.Pattern[str]]] = {}
            for category, pattern_list in pattern_dict.items():
                compiled_patterns[category] = []
                for pattern in pattern_list:
                    try:
                        compiled_patterns[category].append(re.compile(pattern, re.MULTILINE))
                    except re.error as e:
                        self.logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                        continue

            # Process console output line by line
            errors: list[dict[str, Any]] = []
            summary: dict[str, int] = {}
            lines = console_output.splitlines()

            for line_number, line in enumerate(lines, start=1):
                for category, compiled_list in compiled_patterns.items():
                    for compiled_pattern in compiled_list:
                        if compiled_pattern.search(line):
                            errors.append({
                                "line_number": line_number,
                                "line": line,
                                "category": category,
                            })
                            summary[category] = summary.get(category, 0) + 1
                            break  # Only count each line once per category
                    else:
                        continue
                    break  # Only match first category per line

            self.logger.info(
                f"Found {len(errors)} error lines in job '{job_name}' build "
                f"{build_number if build_number else 'latest'}"
            )

            return {
                "errors": errors,
                "summary": summary,
            }

        except JenkinsBuildNotFoundError:
            raise
        except JenkinsApiError:
            raise
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            if "does not exist" in error_msg:
                if "job" in error_msg:
                    raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
                raise JenkinsBuildNotFoundError(f"Build '{job_name}#{build_number}' not found") from e
            elif "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(
                    f"Connection error while getting build errors for '{job_name}#{build_number}': {str(e)}"
                ) from e
            else:
                raise JenkinsApiError(
                    f"Jenkins error getting build errors for '{job_name}#{build_number}': {str(e)}"
                ) from e
        except Exception as e:
            raise JenkinsApiError(
                f"Unexpected error getting build errors for '{job_name}#{build_number}': {str(e)}"
            ) from e

    def enable_job_state(self, job_name: str) -> dict[str, Any]:
        """
        Enable a Jenkins job.

        Args:
            job_name: Name/path of the Jenkins job

        Returns:
            dict: Contains success (bool), job_name, and enabled (bool)

        Raises:
            JenkinsJobNotFoundError: If the job is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info(f"Enabling job: {job_name}")
            self.enable_job(job_name)

            # Verify the job is now enabled by getting job info
            job_info = self.get_job_info(job_name)
            is_enabled = job_info.get("buildable", False)

            self.logger.info(f"Successfully enabled job: {job_name}, enabled: {is_enabled}")
            return {
                "success": True,
                "job_name": job_name,
                "enabled": is_enabled,
            }
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            self.logger.error(f"Jenkins error enabling job '{job_name}': {str(e)}")

            if "does not exist" in error_msg:
                raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
            elif "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(f"Connection error while enabling job '{job_name}': {str(e)}") from e
            else:
                raise JenkinsApiError(f"Jenkins error enabling job '{job_name}': {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error enabling job '{job_name}': {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(error_msg) from e

    def disable_job_state(self, job_name: str) -> dict[str, Any]:
        """
        Disable a Jenkins job.

        Args:
            job_name: Name/path of the Jenkins job

        Returns:
            dict: Contains success (bool), job_name, and enabled (bool)

        Raises:
            JenkinsJobNotFoundError: If the job is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info(f"Disabling job: {job_name}")
            self.disable_job(job_name)

            # Verify the job is now disabled by getting job info
            job_info = self.get_job_info(job_name)
            is_enabled = job_info.get("buildable", True)

            self.logger.info(f"Successfully disabled job: {job_name}, enabled: {is_enabled}")
            return {
                "success": True,
                "job_name": job_name,
                "enabled": is_enabled,
            }
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            self.logger.error(f"Jenkins error disabling job '{job_name}': {str(e)}")

            if "does not exist" in error_msg:
                raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
            elif "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(f"Connection error while disabling job '{job_name}': {str(e)}") from e
            else:
                raise JenkinsApiError(f"Jenkins error disabling job '{job_name}': {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error disabling job '{job_name}': {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(error_msg) from e

    def cancel_build(self, job_name: str, build_number: int | None = None) -> dict[str, Any]:
        """
        Cancel/abort a running Jenkins build.

        Args:
            job_name: Name/path of the Jenkins job
            build_number: Build number to cancel (uses last build if not provided)

        Returns:
            dict: Contains success (bool), job_name, build_number, and message

        Raises:
            JenkinsJobNotFoundError: If the job is not found
            JenkinsBuildNotFoundError: If the build is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info(f"Cancelling build for job: {job_name}, build: {build_number}")

            # Get build number if not provided
            if build_number is None:
                try:
                    job_info = self.get_job_info(job_name)
                except jenkins.JenkinsException as e:
                    error_msg = str(e).lower()
                    if "does not exist" in error_msg:
                        raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
                    raise

                if job_info.get("lastBuild"):
                    build_number = job_info["lastBuild"]["number"]
                else:
                    raise JenkinsBuildNotFoundError(f"No builds found for job '{job_name}'")

            # At this point build_number is guaranteed to be an int
            assert build_number is not None

            # Check if build is already completed before attempting to cancel
            try:
                build_info = self.get_build_info(job_name, build_number)
            except jenkins.JenkinsException as e:
                error_msg = str(e).lower()
                if "does not exist" in error_msg or "not found" in error_msg:
                    raise JenkinsBuildNotFoundError(f"Build '{job_name}#{build_number}' not found") from e
                raise

            result = build_info.get("result")
            if result is not None:
                # Build is already completed
                self.logger.info(f"Build '{job_name}#{build_number}' already completed with result: {result}")
                return {
                    "success": False,
                    "job_name": job_name,
                    "build_number": build_number,
                    "message": f"Build already completed with result: {result}",
                }

            # Use parent class stop_build method to cancel the build
            self.stop_build(job_name, build_number)

            self.logger.info(f"Successfully cancelled build: {job_name}#{build_number}")
            return {
                "success": True,
                "job_name": job_name,
                "build_number": build_number,
                "message": "Build cancelled successfully",
            }
        except JenkinsJobNotFoundError:
            raise
        except JenkinsBuildNotFoundError:
            raise
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            self.logger.error(f"Jenkins error cancelling build '{job_name}#{build_number}': {str(e)}")

            if "does not exist" in error_msg:
                if "job" in error_msg:
                    raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
                raise JenkinsBuildNotFoundError(f"Build '{job_name}#{build_number}' not found") from e
            elif "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(
                    f"Connection error while cancelling build '{job_name}#{build_number}': {str(e)}"
                ) from e
            else:
                raise JenkinsApiError(f"Jenkins error cancelling build '{job_name}#{build_number}': {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error cancelling build '{job_name}#{build_number}': {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(error_msg) from e

    def get_build_parameters(self, job_name: str, build_number: int | None = None) -> dict[str, Any]:
        """
        Get parameters from a specific build.

        Args:
            job_name: Name/path of the Jenkins job
            build_number: Build number to get parameters from (uses last build if not provided)

        Returns:
            dict: Contains job_name, build_number, and parameters (list of {name, value})

        Raises:
            JenkinsJobNotFoundError: If the job is not found
            JenkinsBuildNotFoundError: If the build is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info(f"Getting build parameters for job: {job_name}, build: {build_number}")

            # Get build number if not provided
            if build_number is None:
                try:
                    job_info = self.get_job_info(job_name)
                except jenkins.JenkinsException as e:
                    error_msg = str(e).lower()
                    if "does not exist" in error_msg:
                        raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
                    raise

                if job_info.get("lastBuild"):
                    build_number = job_info["lastBuild"]["number"]
                else:
                    raise JenkinsBuildNotFoundError(f"No builds found for job '{job_name}'")

            # At this point build_number is guaranteed to be an int
            assert build_number is not None

            # Get build info
            try:
                build_info = self.get_build_info(job_name, build_number)
            except jenkins.JenkinsException as e:
                error_msg = str(e).lower()
                if "does not exist" in error_msg or "not found" in error_msg:
                    raise JenkinsBuildNotFoundError(f"Build '{job_name}#{build_number}' not found") from e
                raise

            # Extract parameters from build's actions
            # Look for ParametersAction in the actions array
            parameters: list[dict[str, Any]] = []
            actions = build_info.get("actions", [])
            for action in actions:
                if action is None:
                    continue
                action_class = action.get("_class", "")
                if "ParametersAction" in action_class:
                    params_list = action.get("parameters", [])
                    for param in params_list:
                        if param is None:
                            continue
                        param_name = param.get("name")
                        param_value = param.get("value")
                        if param_name is not None:
                            parameters.append({"name": param_name, "value": param_value})
                    break

            self.logger.info(f"Found {len(parameters)} parameters for build '{job_name}#{build_number}'")

            return {
                "job_name": job_name,
                "build_number": build_number,
                "parameters": parameters,
            }
        except JenkinsBuildNotFoundError:
            raise
        except JenkinsJobNotFoundError:
            raise
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            self.logger.error(f"Jenkins error getting build parameters for '{job_name}#{build_number}': {str(e)}")

            if "does not exist" in error_msg:
                if "job" in error_msg:
                    raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
                raise JenkinsBuildNotFoundError(f"Build '{job_name}#{build_number}' not found") from e
            elif "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(
                    f"Connection error while getting build parameters for '{job_name}#{build_number}': {str(e)}"
                ) from e
            else:
                raise JenkinsApiError(
                    f"Jenkins error getting build parameters for '{job_name}#{build_number}': {str(e)}"
                ) from e
        except Exception as e:
            error_msg = f"Unexpected error getting build parameters for '{job_name}#{build_number}': {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(error_msg) from e

    def monitor_build(
        self,
        job_name: str,
        build_number: int | None = None,
        from_line: int = 0,
    ) -> dict[str, Any]:
        """
        Monitor/stream console output from a build.

        Returns a snapshot of console output from a given line, along with
        build status. Since MCP tools are request-response based (not streaming),
        users can call this repeatedly with increasing from_line to get incremental output.

        Args:
            job_name: Name/path of the Jenkins job
            build_number: Build number to monitor (uses last build if not provided)
            from_line: Start from this line number (default 0)

        Returns:
            dict: Contains job_name, build_number, output (lines from from_line),
                  next_line (for subsequent calls), building (bool), result (str | None)

        Raises:
            ValueError: If from_line is negative
            JenkinsJobNotFoundError: If the job is not found
            JenkinsBuildNotFoundError: If the build is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        # Validate from_line parameter
        if from_line < 0:
            raise ValueError("from_line must be non-negative (>= 0)")

        try:
            self.logger.info(f"Monitoring build for job: {job_name}, build: {build_number}, from_line: {from_line}")

            # Get build number if not provided
            if build_number is None:
                try:
                    job_info = self.get_job_info(job_name)
                except jenkins.JenkinsException as e:
                    error_msg = str(e).lower()
                    if "does not exist" in error_msg:
                        raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
                    raise

                if job_info.get("lastBuild"):
                    build_number = job_info["lastBuild"]["number"]
                else:
                    raise JenkinsBuildNotFoundError(f"No builds found for job '{job_name}'")

            # At this point build_number is guaranteed to be an int
            assert build_number is not None

            # Get build info to check status
            try:
                build_info = self.get_build_info(job_name, build_number)
            except jenkins.JenkinsException as e:
                error_msg = str(e).lower()
                if "does not exist" in error_msg or "not found" in error_msg:
                    raise JenkinsBuildNotFoundError(f"Build '{job_name}#{build_number}' not found") from e
                raise

            # Extract build status
            result = build_info.get("result")
            building = build_info.get("building", False)

            # Get console output
            console_output = self.get_build_console_output(job_name, build_number)

            # Split into lines and extract from from_line onwards
            lines = console_output.splitlines()
            total_lines = len(lines)

            # Get lines from from_line onwards
            if from_line >= total_lines:
                output_lines = []
            else:
                output_lines = lines[from_line:]

            output = "\n".join(output_lines)
            next_line = total_lines

            self.logger.info(
                f"Monitor build '{job_name}#{build_number}': returned {len(output_lines)} lines "
                f"(from {from_line} to {next_line}), building={building}, result={result}"
            )

            return {
                "job_name": job_name,
                "build_number": build_number,
                "output": output,
                "next_line": next_line,
                "building": building,
                "result": result,
            }
        except JenkinsBuildNotFoundError:
            raise
        except JenkinsJobNotFoundError:
            raise
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            self.logger.error(f"Jenkins error monitoring build '{job_name}#{build_number}': {str(e)}")

            if "does not exist" in error_msg:
                if "job" in error_msg:
                    raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
                raise JenkinsBuildNotFoundError(f"Build '{job_name}#{build_number}' not found") from e
            elif "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(
                    f"Connection error while monitoring build '{job_name}#{build_number}': {str(e)}"
                ) from e
            else:
                raise JenkinsApiError(f"Jenkins error monitoring build '{job_name}#{build_number}': {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error monitoring build '{job_name}#{build_number}': {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(error_msg) from e

    def rebuild(self, job_name: str, source_build_number: int) -> dict[str, Any]:
        """
        Rebuild a job with parameters from a previous build.

        Args:
            job_name: Name/path of the Jenkins job
            source_build_number: Build number to copy parameters from

        Returns:
            dict: Contains success (bool), job_name, source_build_number, and new_build_number

        Raises:
            JenkinsJobNotFoundError: If the job is not found
            JenkinsBuildNotFoundError: If the source build is not found
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info(f"Rebuilding job: {job_name} with parameters from build #{source_build_number}")

            # Get build info from source build
            try:
                build_info = self.get_build_info(job_name, source_build_number)
            except jenkins.JenkinsException as e:
                error_msg = str(e).lower()
                if "does not exist" in error_msg or "not found" in error_msg:
                    raise JenkinsBuildNotFoundError(f"Build '{job_name}#{source_build_number}' not found") from e
                raise

            # Extract parameters from build's actions
            # Look for ParametersAction in the actions array
            parameters: dict[str, Any] = {}
            actions = build_info.get("actions", [])
            for action in actions:
                if action is None:
                    continue
                action_class = action.get("_class", "")
                if "ParametersAction" in action_class:
                    params_list = action.get("parameters", [])
                    for param in params_list:
                        if param is None:
                            continue
                        param_name = param.get("name")
                        param_value = param.get("value")
                        if param_name is not None:
                            parameters[param_name] = param_value
                    break

            self.logger.info(f"Extracted {len(parameters)} parameters from build #{source_build_number}")

            # Trigger new build with those parameters
            if parameters:
                self.build_job(job_name, parameters)
            else:
                self.build_job(job_name)

            # Get the new build number
            job_info = self.get_job_info(job_name)
            new_build_number = job_info["nextBuildNumber"] - 1

            self.logger.info(
                f"Successfully triggered rebuild of '{job_name}' from build #{source_build_number}. "
                f"New build number: {new_build_number}"
            )

            return {
                "success": True,
                "job_name": job_name,
                "source_build_number": source_build_number,
                "new_build_number": new_build_number,
            }
        except JenkinsBuildNotFoundError:
            raise
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            self.logger.error(f"Jenkins error rebuilding job '{job_name}': {str(e)}")

            if "does not exist" in error_msg:
                if "job" in error_msg:
                    raise JenkinsJobNotFoundError(f"Job '{job_name}' does not exist") from e
                raise JenkinsBuildNotFoundError(f"Build '{job_name}#{source_build_number}' not found") from e
            elif "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(f"Connection error while rebuilding job '{job_name}': {str(e)}") from e
            else:
                raise JenkinsApiError(f"Jenkins error rebuilding job '{job_name}': {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error rebuilding job '{job_name}': {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(error_msg) from e

    def enable_all_jobs(self, folder: str | None = None, recursive: bool = True) -> dict[str, Any]:
        """
        Bulk enable all disabled jobs in a folder or entire Jenkins instance.

        Args:
            folder: Limit to jobs in this folder path (default: all jobs)
            recursive: Enable jobs in subfolders (default: True)

        Returns:
            dict: Contains count (int) of enabled jobs and enabled_jobs (list of job paths)

        Raises:
            JenkinsConnectionError: If connection to Jenkins fails
            JenkinsApiError: For other Jenkins-related errors
        """
        try:
            self.logger.info(f"Enabling all jobs in folder: {folder or 'all'}, recursive: {recursive}")

            # Get all jobs
            all_jobs = self.get_all_jobs()

            # Filter jobs by folder if specified
            jobs_to_process: list[dict[str, Any]] = []
            for job in all_jobs:
                job_fullname = job.get("fullname", job.get("name", ""))

                if folder:
                    # Normalize folder path (remove leading/trailing slashes)
                    normalized_folder = folder.strip("/")

                    if recursive:
                        # Job should start with folder path
                        if job_fullname.startswith(normalized_folder + "/") or job_fullname == normalized_folder:
                            jobs_to_process.append(cast(dict[str, Any], job))
                    else:
                        # Job should be directly in the folder (one level only)
                        # Check if job is in folder but not in a subfolder
                        if job_fullname.startswith(normalized_folder + "/"):
                            remaining_path = job_fullname[len(normalized_folder) + 1 :]
                            # If there's no more slash, it's a direct child
                            if "/" not in remaining_path:
                                jobs_to_process.append(cast(dict[str, Any], job))
                else:
                    if recursive:
                        # Process all jobs
                        jobs_to_process.append(cast(dict[str, Any], job))
                    else:
                        # Only process top-level jobs (no folder path)
                        if "/" not in job_fullname:
                            jobs_to_process.append(cast(dict[str, Any], job))

            # Enable disabled jobs
            enabled_jobs: list[str] = []
            for job in jobs_to_process:
                job_fullname = job.get("fullname", job.get("name", ""))

                # Check if job is disabled (color ends with _disabled or buildable is False)
                # Jobs can be identified as disabled by their color attribute
                job_color = job.get("color", "")
                is_disabled = job_color.endswith("_disabled") or job_color == "disabled"

                if is_disabled:
                    try:
                        self.enable_job(job_fullname)
                        enabled_jobs.append(job_fullname)
                        self.logger.info(f"Enabled job: {job_fullname}")
                    except jenkins.JenkinsException as e:
                        self.logger.warning(f"Failed to enable job '{job_fullname}': {str(e)}")
                        # Continue with other jobs even if one fails

            self.logger.info(f"Successfully enabled {len(enabled_jobs)} jobs")
            return {
                "count": len(enabled_jobs),
                "enabled_jobs": enabled_jobs,
            }
        except jenkins.JenkinsException as e:
            error_msg = str(e).lower()
            self.logger.error(f"Jenkins error enabling all jobs: {str(e)}")

            if "connection" in error_msg or "timeout" in error_msg:
                raise JenkinsConnectionError(f"Connection error while enabling all jobs: {str(e)}") from e
            else:
                raise JenkinsApiError(f"Jenkins error enabling all jobs: {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error enabling all jobs: {str(e)}"
            self.logger.error(error_msg)
            raise JenkinsApiError(error_msg) from e
