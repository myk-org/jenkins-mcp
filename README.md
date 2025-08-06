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
- **SSL Flexibility**: Configurable SSL verification for internal servers

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/jenkins-mcp.git
   cd jenkins-mcp
   ```

2. Install dependencies using uv:
   ```bash
   uv install
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with your Jenkins server configuration:

```bash
# Jenkins server URL
JENKINS_URL=https://your-jenkins-server.com

# Jenkins authentication
JENKINS_USERNAME=your-username
JENKINS_PASSWORD=your-api-token-or-password
```

### Authentication Recommendations

- **API Token**: Use Jenkins API tokens instead of passwords for better security
- **User Permissions**: Ensure the user has appropriate permissions for the operations you need
- **Network Access**: Verify network connectivity to your Jenkins server

## Usage

### Running the Server

Start the MCP server:
```bash
uv run jenkins-mcp
```

The server will start and listen for MCP client connections.

### Integrating with AI Assistants

Configure your AI assistant to use this MCP server by adding the server configuration to your assistant's settings.

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

## Project Structure

```
jenkins-mcp/
├── mcp_server/
│   ├── __init__.py
│   ├── main.py                    # MCP server entry point
│   └── libs/
│       ├── __init__.py
│       └── jenkins_api.py         # Jenkins API wrapper
├── README.md
├── pyproject.toml                 # Project dependencies and configuration
├── uv.lock                        # Dependency lock file
└── .env.example                   # Environment variable template
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

## Development

### Development Setup

1. Install development dependencies:
   ```bash
   uv install --group dev
   ```

2. Install test dependencies:
   ```bash
   uv install --group tests
   ```

### Code Quality

The project uses several tools to maintain code quality:

- **Ruff**: Code formatting and linting
- **MyPy**: Static type checking
- **Coverage**: Test coverage reporting

Run quality checks:
```bash
# Format code
uv run ruff format

# Check types
uv run mypy mcp_server/

# Run tests with coverage
uv run pytest --cov=mcp_server
```

## Security Considerations

- **Credentials**: Never commit Jenkins credentials to version control
- **SSL Verification**: Consider enabling SSL verification for production environments
- **Permissions**: Use principle of least privilege for Jenkins user accounts
- **Network**: Restrict network access to Jenkins server when possible

## Troubleshooting

### Common Issues

**Connection Errors**
- Verify `JENKINS_URL` is correct and accessible
- Check network connectivity to Jenkins server
- Ensure credentials are valid

**Authentication Failures**
- Use API tokens instead of passwords
- Verify user has necessary permissions
- Check username/token combination

**SSL Certificate Issues**
- For internal servers, SSL verification is disabled by default
- For production, consider proper SSL certificate configuration

### Debug Mode

Enable detailed logging by setting the appropriate log level in your environment.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code quality checks succeed
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review Jenkins server logs
- Verify network connectivity and permissions
- Open an issue on GitHub for bugs or feature requests
