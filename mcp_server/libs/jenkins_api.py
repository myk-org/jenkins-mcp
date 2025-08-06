import os
from typing import Any

import jenkins
from simple_logger.logger import get_logger


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

    def get_job_console(self, job_name: str, build_number: int | None = None) -> str:
        """
        Get console output for a job build.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number (uses latest if not provided)

        Returns:
            str: Console output or error message
        """
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
            return jobs
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
