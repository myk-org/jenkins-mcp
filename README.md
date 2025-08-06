# Jenkins MCP Server

A Model Context Protocol (MCP) server that provides Jenkins automation tools using FastMCP.

## Overview

This MCP server enables AI assistants to interact with Jenkins CI/CD servers through a standardized interface. It provides tools for managing Jenkins jobs, retrieving build information, accessing console outputs, and monitoring build status - all through simple, secure API calls.

## Features

- **Job Management**: Get comprehensive job information including configuration and build history
- **Build Execution**: Trigger job execution with optional parameters
- **Console Access**: Retrieve console output for specific builds
- **Server Information**: Get Jenkins server version and status
- **Job Discovery**: List all available Jenkins jobs
- **Secure Authentication**: Environment-based credential management

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/jenkins-mcp.git
   cd jenkins-mcp
   ```

2. Install dependencies using uv:

   ```bash
   uv sync
   ```

## Configuration

### Authentication Recommendations

- **API Token**: Use Jenkins API tokens instead of passwords for better security
- **User Permissions**: Ensure the user has appropriate permissions for the operations you need
- **Network Access**: Verify network connectivity to your Jenkins server

### MCP Client Configuration

Add this server to your MCP client configuration. For Claude Desktop, add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jenkins-mcp": {
      "command": "uv",
      "args": [
        "run",
        "/path/to/jenkins-mcp/.venv/bin/python",
        "/path/to/jenkins-mcp/mcp_server/main.py"
      ],
      "env": {
        "JENKINS_URL": "https://your-jenkins-server.com",
        "JENKINS_USERNAME": "your-username",
        "JENKINS_PASSWORD": "your-api-token"  # pragma: allowlist secret
      }
    }
  }
}
```

Replace `/path/to/jenkins-mcp` with the actual path where you cloned this repository.
Replace the paths and credentials with your actual Jenkins server information.

## Available Tools

### `get-version`

Get Jenkins server version information.

**Parameters:** None

**Returns:** Jenkins server version string

**Example:**

```
Jenkins version: 2.414.1
```

### `job-info`

Get comprehensive information about a Jenkins job including configuration, last build status, build history, and metadata.

**Parameters:**

- `job_name` (string): The name of the Jenkins job

**Returns:** JSON object containing complete job information

**Example:**

```json
{
  "name": "my-build-job",
  "url": "https://jenkins.example.com/job/my-build-job/",
  "buildable": true,
  "builds": [...],
  "lastBuild": {...},
  "lastSuccessfulBuild": {...}
}
```

### `run-job`

Trigger a Jenkins job to run with optional parameters.

**Parameters:**

- `job_name` (string): The name of the Jenkins job to run
- `parameters` (string): JSON string containing job parameters (optional)

**Returns:** Success message with build information or error message

**Example:**

```bash
# Without parameters
run-job("my-build-job")

# With parameters
run-job("my-build-job", '{"branch": "main", "environment": "staging"}')
```

### `job-console`

Get the console output for a specific Jenkins job build.

**Parameters:**

- `job_name` (string): The name of the Jenkins job
- `build_number` (int, optional): The build number (uses latest build if not provided)

**Returns:** Console output text

**Example:**

```
Started by user admin
Running in Durability level: MAX_SURVIVABILITY
[Pipeline] Start of Pipeline
[Pipeline] node
Running on Jenkins in /var/jenkins_home/workspace/my-build-job
...
```

### `get-jobs`

Get a list of all Jenkins jobs.

**Parameters:** None

**Returns:** JSON array containing all job information

**Example:**

```json
[
  {
    "name": "job1",
    "url": "https://jenkins.example.com/job/job1/",
    "color": "blue"
  },
  {
    "name": "job2",
    "url": "https://jenkins.example.com/job/job2/",
    "color": "red"
  }
]
```

## Requirements

- **Python**: >= 3.12
- **Jenkins Server**: Access to a Jenkins server with appropriate permissions
- **Network**: Connectivity to Jenkins server
- **Authentication**: Valid Jenkins credentials (username and API token recommended)

## Dependencies

- **fastmcp**: >= 2.11.1 - MCP server framework
- **python-jenkins**: >= 1.8.3 - Jenkins API client
- **python-simple-logger**: >= 2.0.16 - Logging utilities

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code quality checks succeed
6. Submit a pull request

## Support

For issues and questions:

- Check the troubleshooting section above
- Review Jenkins server logs
- Verify network connectivity and permissions
- Open an issue on GitHub for bugs or feature requests
