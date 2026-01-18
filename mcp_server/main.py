import json
from fastmcp import FastMCP
from simple_logger.logger import get_logger

from mcp_server.libs.jenkins_api import (
    JenkinsApi,
    JenkinsApiError,
    JenkinsBuildNotFoundError,
    JenkinsConnectionError,
    JenkinsJobNotFoundError,
)

# Initialize logger
logger = get_logger(__name__)

# Create MCP server
mcp = FastMCP("Jenkins MCP Server")

# Global Jenkins API instance
jenkins_api: JenkinsApi | None = None


def get_jenkins_api() -> JenkinsApi:
    """Get or create Jenkins API instance."""
    global jenkins_api
    if jenkins_api is None:
        jenkins_api = JenkinsApi()
    return jenkins_api


@mcp.tool(name="get-version")
def jenkins_get_version() -> str:
    """
    Get Jenkins server version information.

    Returns:
        str: Jenkins server version
    """
    try:
        api = get_jenkins_api()
        version = api.get_version()
        logger.info(f"Jenkins version: {version}")
        return f"Jenkins version: {version}"
    except Exception as e:
        logger.error(f"Failed to get Jenkins version: {e}")
        return f"Error getting Jenkins version: {str(e)}"


@mcp.tool(name="job-info")
def jenkins_get_job_info(job_name: str) -> str:
    """
    Get comprehensive information about a Jenkins job including configuration,
    last build status, build history, and other job metadata.

    Args:
        job_name: The name of the Jenkins job to get information for

    Returns:
        str: JSON string containing job information or error message
    """
    try:
        api = get_jenkins_api()
        job_info = api.get_job_details(job_name)
        logger.info(f"Successfully retrieved job info for: {job_name}")
        return json.dumps(job_info, indent=2)
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to get job info for '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="run-job")
def jenkins_run_job(job_name: str, parameters: str = "{}") -> str:
    """
    Trigger a Jenkins job to run with optional parameters.

    Args:
        job_name: The name of the Jenkins job to run
        parameters: JSON string containing job parameters (default: empty dict)

    Returns:
        str: Success message with build information or error message
    """
    try:
        api = get_jenkins_api()

        # Parse parameters JSON string
        try:
            parsed_parameters = json.loads(parameters) if parameters.strip() else {}
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in parameters: {str(e)}"
            logger.error(error_msg)
            return error_msg

        result = api.run_job(job_name, parsed_parameters if parsed_parameters else None)
        return result
    except Exception as e:
        error_msg = f"Failed to run job '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="job-console")
def jenkins_get_job_console(
    job_name: str,
    build_number: int | None = None,
    tail: int | None = None,
    head: int | None = None,
) -> str:
    """
    Get the console output for a specific Jenkins job build.

    Args:
        job_name: The name of the Jenkins job
        build_number: The build number to get console output for (uses latest build if not provided)
        tail: Return only the last N lines of output (mutually exclusive with head)
        head: Return only the first N lines of output (mutually exclusive with tail)

    Returns:
        str: Console output text or error message
    """
    try:
        api = get_jenkins_api()
        console_output = api.get_job_console(job_name, build_number, tail=tail, head=head)
        return console_output
    except ValueError as e:
        error_msg = f"Invalid parameters: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to get console output for '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="get-jobs")
def jenkins_get_jobs() -> str:
    """
    Get a list of all Jenkins jobs.

    Returns:
        str: JSON string containing list of all jobs or error message
    """
    try:
        api = get_jenkins_api()
        jobs = api.get_all_jobs_list()
        logger.info(f"Successfully retrieved {len(jobs)} jobs")
        return json.dumps(jobs, indent=2)
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to get jobs list: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="wait-for-build")
def jenkins_wait_for_build(
    job_name: str,
    build_number: int | None = None,
    timeout: int = 3600,
    poll_interval: int = 30,
) -> str:
    """
    Wait for a Jenkins build to complete and return its result.

    Args:
        job_name: The name/path of the Jenkins job
        build_number: Specific build number to wait for (uses last build if not provided)
        timeout: Maximum wait time in seconds (default: 3600)
        poll_interval: Seconds between status checks (default: 30)

    Returns:
        str: JSON string containing build_number, result, duration, and url
    """
    try:
        api = get_jenkins_api()
        result = api.wait_for_build(
            job_name=job_name,
            build_number=build_number,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        logger.info(f"Build '{job_name}#{result['build_number']}' completed: {result['result']}")
        return json.dumps(result, indent=2)
    except ValueError as e:
        error_msg = f"Invalid parameters: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsBuildNotFoundError as e:
        error_msg = f"Build not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to wait for build '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="get-build-errors")
def jenkins_get_build_errors(
    job_name: str,
    build_number: int | None = None,
    patterns: str = "[]",
) -> str:
    """
    Extract errors from build console output using regex patterns.

    Args:
        job_name: The name/path of the Jenkins job
        build_number: Specific build number (uses last build if not provided)
        patterns: JSON string array of custom regex patterns (uses default patterns if empty)

    Returns:
        str: JSON string containing errors (list of {line_number, line, category})
             and summary (count by category)
    """
    try:
        api = get_jenkins_api()

        # Parse patterns JSON string
        try:
            parsed_patterns = json.loads(patterns) if patterns.strip() else []
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in patterns: {str(e)}"
            logger.error(error_msg)
            return error_msg

        # Validate that parsed_patterns is a list of strings
        if not isinstance(parsed_patterns, list):
            error_msg = "patterns must be a JSON array of strings"
            logger.error(error_msg)
            return error_msg
        for i, pattern in enumerate(parsed_patterns):
            if not isinstance(pattern, str):
                error_msg = f"patterns[{i}] must be a string, got {type(pattern).__name__}"
                logger.error(error_msg)
                return error_msg

        # Pass None if patterns list is empty to use defaults
        patterns_list = parsed_patterns if parsed_patterns else None

        result = api.get_build_errors(
            job_name=job_name,
            build_number=build_number,
            patterns=patterns_list,
        )
        logger.info(
            f"Found {len(result['errors'])} errors in '{job_name}' build {build_number if build_number else 'latest'}"
        )
        return json.dumps(result, indent=2)
    except JenkinsBuildNotFoundError as e:
        error_msg = f"Build not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to get build errors for '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="enable-job")
def jenkins_enable_job(job_name: str) -> str:
    """
    Enable a disabled Jenkins job.

    Args:
        job_name: The name/path of the Jenkins job to enable

    Returns:
        str: JSON string containing success status, job_name, and enabled state
    """
    try:
        api = get_jenkins_api()
        result = api.enable_job_state(job_name)
        logger.info(f"Job '{job_name}' enabled: {result['enabled']}")
        return json.dumps(result, indent=2)
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to enable job '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="disable-job")
def jenkins_disable_job(job_name: str) -> str:
    """
    Disable a Jenkins job.

    Args:
        job_name: The name/path of the Jenkins job to disable

    Returns:
        str: JSON string containing success status, job_name, and enabled state
    """
    try:
        api = get_jenkins_api()
        result = api.disable_job_state(job_name)
        logger.info(f"Job '{job_name}' disabled: enabled={result['enabled']}")
        return json.dumps(result, indent=2)
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to disable job '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="rebuild")
def jenkins_rebuild(job_name: str, source_build_number: int) -> str:
    """
    Rebuild a Jenkins job with parameters from a previous build.

    Args:
        job_name: The name/path of the Jenkins job to rebuild
        source_build_number: Build number to copy parameters from

    Returns:
        str: JSON string containing success status, job_name, source_build_number, and new_build_number
    """
    try:
        api = get_jenkins_api()
        result = api.rebuild(job_name, source_build_number)
        logger.info(
            f"Rebuild triggered for '{job_name}' from build #{source_build_number}. "
            f"New build number: {result['new_build_number']}"
        )
        return json.dumps(result, indent=2)
    except JenkinsBuildNotFoundError as e:
        error_msg = f"Build not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to rebuild job '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="get-build-parameters")
def jenkins_get_build_parameters(job_name: str, build_number: int | None = None) -> str:
    """
    Get parameters from a specific Jenkins build.

    Args:
        job_name: The name/path of the Jenkins job
        build_number: Specific build number to get parameters from (uses last build if not provided)

    Returns:
        str: JSON string containing job_name, build_number, and parameters (list of {name, value})
    """
    try:
        api = get_jenkins_api()
        result = api.get_build_parameters(job_name, build_number)
        logger.info(f"Retrieved {len(result['parameters'])} parameters from '{job_name}#{result['build_number']}'")
        return json.dumps(result, indent=2)
    except JenkinsBuildNotFoundError as e:
        error_msg = f"Build not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to get build parameters for '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="monitor-build")
def jenkins_monitor_build(
    job_name: str,
    build_number: int | None = None,
    from_line: int = 0,
) -> str:
    """
    Monitor/stream console output from a build.

    Returns a snapshot of console output from a given line, along with build status.
    Since MCP tools are request-response based (not streaming), call this repeatedly
    with increasing from_line to get incremental output.

    Args:
        job_name: The name/path of the Jenkins job
        build_number: Specific build number to monitor (uses last build if not provided)
        from_line: Start from this line number (default 0)

    Returns:
        str: JSON string containing job_name, build_number, output (lines from from_line),
             next_line (for subsequent calls), building (bool), result (str | None)
    """
    try:
        api = get_jenkins_api()
        result = api.monitor_build(
            job_name=job_name,
            build_number=build_number,
            from_line=from_line,
        )
        logger.info(
            f"Monitor build '{job_name}#{result['build_number']}': "
            f"building={result['building']}, result={result['result']}"
        )
        return json.dumps(result, indent=2)
    except ValueError as e:
        error_msg = f"Invalid parameters: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsBuildNotFoundError as e:
        error_msg = f"Build not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to monitor build for '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="cancel-build")
def jenkins_cancel_build(job_name: str, build_number: int | None = None) -> str:
    """
    Cancel/abort a running Jenkins build.

    Args:
        job_name: The name/path of the Jenkins job
        build_number: Specific build number to cancel (uses last build if not provided)

    Returns:
        str: JSON string containing success status, job_name, and build_number
    """
    try:
        api = get_jenkins_api()
        result = api.cancel_build(job_name, build_number)
        logger.info(f"Cancelled build '{job_name}#{result['build_number']}'")
        return json.dumps(result, indent=2)
    except JenkinsBuildNotFoundError as e:
        error_msg = f"Build not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsJobNotFoundError as e:
        error_msg = f"Job not found: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to cancel build for '{job_name}': {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool(name="enable-all-jobs")
def jenkins_enable_all_jobs(folder: str | None = None, recursive: bool = True) -> str:
    """
    Bulk enable all disabled jobs in a folder or entire Jenkins instance.

    Args:
        folder: Limit to jobs in this folder path (default: all jobs)
        recursive: Enable jobs in subfolders (default: True)

    Returns:
        str: JSON string containing count of enabled jobs and list of enabled job paths
    """
    try:
        api = get_jenkins_api()
        result = api.enable_all_jobs(folder=folder, recursive=recursive)
        logger.info(f"Enabled {result['count']} jobs")
        return json.dumps(result, indent=2)
    except JenkinsConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except JenkinsApiError as e:
        error_msg = f"Jenkins API error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to enable all jobs: {str(e)}"
        logger.error(error_msg)
        return error_msg


if __name__ == "__main__":
    logger.info("Starting Jenkins MCP Server")
    mcp.run()
