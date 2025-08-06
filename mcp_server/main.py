import json
from fastmcp import FastMCP
from simple_logger.logger import get_logger

from mcp_server.libs.jenkins_api import (
    JenkinsApi,
    JenkinsApiError,
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
def jenkins_get_job_console(job_name: str, build_number: int | None = None) -> str:
    """
    Get the console output for a specific Jenkins job build.

    Args:
        job_name: The name of the Jenkins job
        build_number: The build number to get console output for (uses latest build if not provided)

    Returns:
        str: Console output text or error message
    """
    try:
        api = get_jenkins_api()
        console_output = api.get_job_console(job_name, build_number)
        return console_output
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


if __name__ == "__main__":
    logger.info("Starting Jenkins MCP Server")
    mcp.run()
