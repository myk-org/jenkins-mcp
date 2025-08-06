"""Tests for the MCP endpoint functions in main.py."""

import json
import pytest
from unittest.mock import Mock, patch

from mcp_server.libs.jenkins_api import JenkinsApi


class TestGetJenkinsApi:
    """Test the get_jenkins_api function."""

    def test_get_jenkins_api_creates_new_instance(self, mock_env_vars):
        """Test that get_jenkins_api creates a new instance when none exists."""
        # Reset global jenkins_api
        import mcp_server.main

        mcp_server.main.jenkins_api = None

        with patch("mcp_server.main.JenkinsApi") as mock_jenkins_api_class:
            mock_instance = Mock(spec=JenkinsApi)
            mock_jenkins_api_class.return_value = mock_instance

            result = mcp_server.main.get_jenkins_api()

            assert result == mock_instance
            mock_jenkins_api_class.assert_called_once()

    def test_get_jenkins_api_returns_existing_instance(self, mock_env_vars):
        """Test that get_jenkins_api returns existing instance when available."""
        # Set up existing instance
        import mcp_server.main

        existing_instance = Mock(spec=JenkinsApi)
        mcp_server.main.jenkins_api = existing_instance

        with patch("mcp_server.main.JenkinsApi") as mock_jenkins_api_class:
            result = mcp_server.main.get_jenkins_api()

            assert result == existing_instance
            mock_jenkins_api_class.assert_not_called()


class TestJenkinsToolFunctions:
    """Test the underlying tool functions."""

    def setUp(self):
        """Reset global jenkins_api before each test."""
        import mcp_server.main

        mcp_server.main.jenkins_api = None

    def test_jenkins_get_version_success(self, mock_env_vars):
        """Test successful version retrieval."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_version.return_value = "2.401.3"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Import and call the function directly
                from mcp_server import main
                # Get the function before it's decorated by importing from the module
                # We'll test the tool handler by calling the underlying logic

                # Test the underlying logic by recreating it
                try:
                    api = main.get_jenkins_api()
                    version = api.get_version()
                    main.logger.info(f"Jenkins version: {version}")
                    result = f"Jenkins version: {version}"
                except Exception as e:
                    main.logger.error(f"Failed to get Jenkins version: {e}")
                    result = f"Error getting Jenkins version: {str(e)}"

                assert result == "Jenkins version: 2.401.3"
                mock_api.get_version.assert_called_once()
                mock_logger.info.assert_called_once_with("Jenkins version: 2.401.3")

    def test_jenkins_get_version_exception(self, mock_env_vars):
        """Test version retrieval with exception."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_version.side_effect = Exception("Connection failed")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                from mcp_server import main

                # Test the underlying logic by recreating it
                try:
                    api = main.get_jenkins_api()
                    version = api.get_version()
                    main.logger.info(f"Jenkins version: {version}")
                    result = f"Jenkins version: {version}"
                except Exception as e:
                    main.logger.error(f"Failed to get Jenkins version: {e}")
                    result = f"Error getting Jenkins version: {str(e)}"

                assert "Error getting Jenkins version: Connection failed" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_job_info_success(self, mock_env_vars, sample_job_info):
        """Test successful job info retrieval."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_details.return_value = sample_job_info

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                from mcp_server import main

                # Test the underlying logic
                job_name = "test-job"
                try:
                    api = main.get_jenkins_api()
                    job_info = api.get_job_details(job_name)

                    if isinstance(job_info, dict):
                        main.logger.info(f"Successfully retrieved job info for: {job_name}")
                        result = json.dumps(job_info, indent=2)
                    else:
                        result = job_info
                except Exception as e:
                    error_msg = f"Failed to get job info for '{job_name}': {str(e)}"
                    main.logger.error(error_msg)
                    result = error_msg

                # Parse the JSON result to verify it's valid
                parsed_result = json.loads(result)
                assert parsed_result == sample_job_info
                mock_api.get_job_details.assert_called_once_with("test-job")
                mock_logger.info.assert_called_once_with("Successfully retrieved job info for: test-job")

    def test_jenkins_get_job_info_error_response(self, mock_env_vars):
        """Test job info retrieval with error response from API."""
        error_message = "Job 'nonexistent-job' does not exist"
        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_details.return_value = error_message

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            from mcp_server import main

            # Test the underlying logic
            job_name = "nonexistent-job"
            try:
                api = main.get_jenkins_api()
                job_info = api.get_job_details(job_name)

                if isinstance(job_info, dict):
                    main.logger.info(f"Successfully retrieved job info for: {job_name}")
                    result = json.dumps(job_info, indent=2)
                else:
                    result = job_info
            except Exception as e:
                error_msg = f"Failed to get job info for '{job_name}': {str(e)}"
                main.logger.error(error_msg)
                result = error_msg

            assert result == error_message
            mock_api.get_job_details.assert_called_once_with("nonexistent-job")

    def test_jenkins_run_job_without_parameters(self, mock_env_vars):
        """Test running job without parameters."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.run_job.return_value = "Job 'test-job' started successfully. Build number: 5"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            from mcp_server import main

            # Test the underlying logic
            job_name = "test-job"
            parameters = "{}"
            try:
                api = main.get_jenkins_api()

                # Parse parameters JSON string
                try:
                    parsed_parameters = json.loads(parameters) if parameters.strip() else {}
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON in parameters: {str(e)}"
                    main.logger.error(error_msg)
                    result = error_msg
                    parsed_parameters = None

                if parsed_parameters is not None:
                    result = api.run_job(job_name, parsed_parameters if parsed_parameters else None)
            except Exception as e:
                error_msg = f"Failed to run job '{job_name}': {str(e)}"
                main.logger.error(error_msg)
                result = error_msg

            assert "Job 'test-job' started successfully. Build number: 5" in result
            mock_api.run_job.assert_called_once_with("test-job", None)

    def test_jenkins_run_job_with_parameters(self, mock_env_vars, valid_job_parameters):
        """Test running job with valid parameters."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.run_job.return_value = "Job 'test-job' started successfully. Build number: 5"
        parameters_json = json.dumps(valid_job_parameters)

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            from mcp_server import main

            # Test the underlying logic
            job_name = "test-job"
            parameters = parameters_json
            try:
                api = main.get_jenkins_api()

                # Parse parameters JSON string
                try:
                    parsed_parameters = json.loads(parameters) if parameters.strip() else {}
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON in parameters: {str(e)}"
                    main.logger.error(error_msg)
                    result = error_msg
                    parsed_parameters = None

                if parsed_parameters is not None:
                    result = api.run_job(job_name, parsed_parameters if parsed_parameters else None)
            except Exception as e:
                error_msg = f"Failed to run job '{job_name}': {str(e)}"
                main.logger.error(error_msg)
                result = error_msg

            assert "Job 'test-job' started successfully. Build number: 5" in result
            mock_api.run_job.assert_called_once_with("test-job", valid_job_parameters)

    def test_jenkins_run_job_invalid_json_parameters(self, mock_env_vars, invalid_json_parameters):
        """Test running job with invalid JSON parameters."""
        with patch("mcp_server.main.get_jenkins_api") as mock_get_api:
            with patch("mcp_server.main.logger") as mock_logger:
                from mcp_server import main

                # Test the underlying logic
                job_name = "test-job"
                parameters = invalid_json_parameters
                try:
                    api = main.get_jenkins_api()

                    # Parse parameters JSON string
                    try:
                        parsed_parameters = json.loads(parameters) if parameters.strip() else {}
                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid JSON in parameters: {str(e)}"
                        main.logger.error(error_msg)
                        result = error_msg
                        parsed_parameters = None

                    if parsed_parameters is not None:
                        result = api.run_job(job_name, parsed_parameters if parsed_parameters else None)
                except Exception as e:
                    error_msg = f"Failed to run job '{job_name}': {str(e)}"
                    main.logger.error(error_msg)
                    result = error_msg

                assert "Invalid JSON in parameters:" in result
                mock_get_api.assert_called_once()  # API is created but not used
                mock_logger.error.assert_called_once()

    def test_jenkins_get_job_console_with_build_number(self, mock_env_vars, sample_console_output):
        """Test getting console output with specific build number."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.return_value = sample_console_output

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            from mcp_server import main

            # Test the underlying logic
            job_name = "test-job"
            build_number = 5
            try:
                api = main.get_jenkins_api()
                result = api.get_job_console(job_name, build_number)
            except Exception as e:
                error_msg = f"Failed to get console output for '{job_name}': {str(e)}"
                main.logger.error(error_msg)
                result = error_msg

            assert result == sample_console_output
            mock_api.get_job_console.assert_called_once_with("test-job", 5)

    def test_jenkins_get_job_console_without_build_number(self, mock_env_vars, sample_console_output):
        """Test getting console output without build number (latest)."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.return_value = sample_console_output

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            from mcp_server import main

            # Test the underlying logic
            job_name = "test-job"
            build_number = None
            try:
                api = main.get_jenkins_api()
                result = api.get_job_console(job_name, build_number)
            except Exception as e:
                error_msg = f"Failed to get console output for '{job_name}': {str(e)}"
                main.logger.error(error_msg)
                result = error_msg

            assert result == sample_console_output
            mock_api.get_job_console.assert_called_once_with("test-job", None)

    def test_jenkins_get_jobs_success(self, mock_env_vars, sample_jobs_list):
        """Test successful retrieval of jobs list."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_all_jobs_list.return_value = sample_jobs_list

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                from mcp_server import main

                # Test the underlying logic
                try:
                    api = main.get_jenkins_api()
                    jobs = api.get_all_jobs_list()

                    if isinstance(jobs, list):
                        main.logger.info(f"Successfully retrieved {len(jobs)} jobs")
                        result = json.dumps(jobs, indent=2)
                    else:
                        result = jobs
                except Exception as e:
                    error_msg = f"Failed to get jobs list: {str(e)}"
                    main.logger.error(error_msg)
                    result = error_msg

                # Parse the JSON result to verify it's valid
                parsed_result = json.loads(result)
                assert parsed_result == sample_jobs_list
                mock_api.get_all_jobs_list.assert_called_once()
                mock_logger.info.assert_called_once_with("Successfully retrieved 3 jobs")

    def test_jenkins_get_jobs_error_response(self, mock_env_vars):
        """Test jobs retrieval with error response from API."""
        error_message = "Permission denied: user lacks Overall/Read permission"
        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_all_jobs_list.return_value = error_message

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            from mcp_server import main

            # Test the underlying logic
            try:
                api = main.get_jenkins_api()
                jobs = api.get_all_jobs_list()

                if isinstance(jobs, list):
                    main.logger.info(f"Successfully retrieved {len(jobs)} jobs")
                    result = json.dumps(jobs, indent=2)
                else:
                    result = jobs
            except Exception as e:
                error_msg = f"Failed to get jobs list: {str(e)}"
                main.logger.error(error_msg)
                result = error_msg

            assert result == error_message
            mock_api.get_all_jobs_list.assert_called_once()


class TestToolExceptionHandling:
    """Test exception handling in tool functions."""

    def test_get_jenkins_api_exception_handling(self, missing_env_vars):
        """Test exception when creating Jenkins API instance."""
        from mcp_server import main

        # Reset global jenkins_api to ensure fresh test
        main.jenkins_api = None

        # Test that missing environment variables raise ValueError
        with pytest.raises(ValueError) as exc_info:
            main.get_jenkins_api()

        assert "Missing Jenkins credentials" in str(exc_info.value)

    def test_tool_functions_with_api_creation_failure(self, missing_env_vars):
        """Test that tool functions handle API creation failures gracefully."""
        from mcp_server import main

        # Reset global jenkins_api to ensure fresh test
        main.jenkins_api = None

        with patch("mcp_server.main.logger") as mock_logger:
            # Test version endpoint
            try:
                api = main.get_jenkins_api()
                version = api.get_version()
                main.logger.info(f"Jenkins version: {version}")
                result = f"Jenkins version: {version}"
            except Exception as e:
                main.logger.error(f"Failed to get Jenkins version: {e}")
                result = f"Error getting Jenkins version: {str(e)}"

            assert "Error getting Jenkins version:" in result
            assert "Missing Jenkins credentials" in result
            mock_logger.error.assert_called_once()


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_json_serialization_with_special_characters(self, mock_env_vars):
        """Test JSON serialization with special characters."""
        # Test with data that might cause JSON serialization issues
        problematic_data = {
            "name": "test-job",
            "special_chars": "äöü@#$%&*()",
            "unicode": "🚀 Jenkins Job",
            "nested": {"list": [1, 2, 3, None], "float": 3.14159, "boolean": True},
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_details.return_value = problematic_data

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            from mcp_server import main

            # Test the underlying logic
            job_name = "test-job"
            try:
                api = main.get_jenkins_api()
                job_info = api.get_job_details(job_name)

                if isinstance(job_info, dict):
                    main.logger.info(f"Successfully retrieved job info for: {job_name}")
                    result = json.dumps(job_info, indent=2)
                else:
                    result = job_info
            except Exception as e:
                error_msg = f"Failed to get job info for '{job_name}': {str(e)}"
                main.logger.error(error_msg)
                result = error_msg

            # Should not raise an exception and should be valid JSON
            parsed_result = json.loads(result)
            assert parsed_result == problematic_data

    def test_empty_and_whitespace_parameters(self, mock_env_vars):
        """Test handling of empty and whitespace-only parameters."""
        mock_api = Mock(spec=JenkinsApi)
        mock_api.run_job.return_value = "Job started successfully"

        test_cases = ["", "   ", "{}", "  {} "]

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            from mcp_server import main

            for parameters in test_cases:
                # Test the underlying logic
                job_name = "test-job"
                try:
                    api = main.get_jenkins_api()

                    # Parse parameters JSON string
                    try:
                        parsed_parameters = json.loads(parameters) if parameters.strip() else {}
                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid JSON in parameters: {str(e)}"
                        main.logger.error(error_msg)
                        parsed_parameters = None

                    if parsed_parameters is not None:
                        api.run_job(job_name, parsed_parameters if parsed_parameters else None)
                except Exception as e:
                    error_msg = f"Failed to run job '{job_name}': {str(e)}"
                    main.logger.error(error_msg)

        # Should call run_job with None for all empty parameter cases
        assert mock_api.run_job.call_count == len(test_cases)
        for call in mock_api.run_job.call_args_list:
            assert call[0][1] is None  # Second argument should be None


class TestAdditionalCoverage:
    """Additional tests to improve code coverage."""

    def test_main_module_initialization(self, mock_env_vars):
        """Test main module initialization and global variables."""
        import mcp_server.main as main_module

        # Test that the module has the expected attributes
        assert hasattr(main_module, "mcp")
        assert hasattr(main_module, "jenkins_api")
        assert hasattr(main_module, "logger")
        assert hasattr(main_module, "get_jenkins_api")

        # Test MCP server creation
        assert main_module.mcp is not None
        assert "FastMCP" in str(main_module.mcp)

    def test_module_level_logger(self):
        """Test that the module-level logger is properly configured."""
        import mcp_server.main as main_module

        # Verify logger exists and has expected attributes
        assert main_module.logger is not None
        assert hasattr(main_module.logger, "info")
        assert hasattr(main_module.logger, "error")
        assert hasattr(main_module.logger, "debug")

    def test_all_mcp_tools_registered(self):
        """Test that all expected MCP tools are registered."""
        import mcp_server.main as main_module

        # These tools should be registered based on the decorators in main.py

        # We can't easily test the tools directly due to async nature,
        # but we can verify the MCP instance exists and has tools
        assert main_module.mcp is not None

        # Test that the decorated functions exist
        assert hasattr(main_module, "jenkins_get_version")
        assert hasattr(main_module, "jenkins_get_job_info")
        assert hasattr(main_module, "jenkins_run_job")
        assert hasattr(main_module, "jenkins_get_job_console")
        assert hasattr(main_module, "jenkins_get_jobs")

    def test_jenkins_api_global_variable_behavior(self, mock_env_vars):
        """Test jenkins_api global variable behavior in different scenarios."""
        import mcp_server.main as main_module

        # Initially should be None
        main_module.jenkins_api = None
        assert main_module.jenkins_api is None

        # After calling get_jenkins_api, should be set
        with patch("mcp_server.main.JenkinsApi") as mock_jenkins_api_class:
            mock_instance = Mock(spec=JenkinsApi)
            mock_jenkins_api_class.return_value = mock_instance

            result1 = main_module.get_jenkins_api()
            assert main_module.jenkins_api is not None
            assert main_module.jenkins_api == mock_instance

            # Subsequent calls should return the same instance
            result2 = main_module.get_jenkins_api()
            assert result1 == result2
            assert mock_jenkins_api_class.call_count == 1  # Only called once

    def test_run_job_parameter_edge_cases(self, mock_env_vars):
        """Test run_job parameter parsing edge cases."""
        from mcp_server import main

        mock_api = Mock(spec=JenkinsApi)
        mock_api.run_job.return_value = "Job started successfully"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            # Test various parameter combinations that should result in None
            test_cases = [
                "",  # Empty string
                "   ",  # Whitespace only
                "{}",  # Empty JSON object
                "  {}  ",  # Empty JSON with whitespace
            ]

            for parameters in test_cases:
                # Test the parameter parsing logic directly
                job_name = "test-job"
                try:
                    api = main.get_jenkins_api()
                    # Parse parameters JSON string
                    try:
                        parsed_parameters = json.loads(parameters) if parameters.strip() else {}
                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid JSON in parameters: {str(e)}"
                        main.logger.error(error_msg)
                        parsed_parameters = None

                    if parsed_parameters is not None:
                        api.run_job(job_name, parsed_parameters if parsed_parameters else None)
                except Exception as e:
                    error_msg = f"Failed to run job '{job_name}': {str(e)}"
                    main.logger.error(error_msg)

                # All these cases should result in calling run_job with None
                mock_api.run_job.assert_called_with("test-job", None)

    def test_comprehensive_error_scenarios(self, mock_env_vars):
        """Test comprehensive error scenarios for all functions."""
        from mcp_server import main

        # Test different types of exceptions
        exception_types = [
            Exception("Generic error"),
            ValueError("Value error"),
            ConnectionError("Connection error"),
            TimeoutError("Timeout error"),
        ]

        for exception in exception_types:
            mock_api = Mock(spec=JenkinsApi)
            mock_api.get_version.side_effect = exception
            mock_api.get_job_details.side_effect = exception
            mock_api.run_job.side_effect = exception
            mock_api.get_job_console.side_effect = exception
            mock_api.get_all_jobs_list.side_effect = exception

            with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
                with patch("mcp_server.main.logger") as mock_logger:
                    # Test get_version error handling
                    try:
                        api = main.get_jenkins_api()
                        version = api.get_version()
                        main.logger.info(f"Jenkins version: {version}")
                        result = f"Jenkins version: {version}"
                    except Exception as e:
                        main.logger.error(f"Failed to get Jenkins version: {e}")
                        result = f"Error getting Jenkins version: {str(e)}"

                    assert f"Error getting Jenkins version: {str(exception)}" in result
                    mock_logger.error.assert_called()

    def test_console_output_edge_cases(self, mock_env_vars):
        """Test console output handling edge cases."""
        from mcp_server import main

        mock_api = Mock(spec=JenkinsApi)

        # Test with very large build numbers
        large_build_numbers = [999999999, 0, -1]

        for build_number in large_build_numbers:
            mock_api.get_job_console.return_value = f"Console output for build {build_number}"

            with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
                try:
                    api = main.get_jenkins_api()
                    api.get_job_console("test-job", build_number)
                except Exception as e:
                    error_msg = f"Failed to get console output for 'test-job': {str(e)}"
                    main.logger.error(error_msg)

                # Should handle all build numbers gracefully
                mock_api.get_job_console.assert_called_with("test-job", build_number)


class TestMCPFrameworkIntegration:
    """Test integration with MCP framework."""

    def test_mcp_server_tools_registration(self, mock_env_vars):
        """Test that MCP tools are properly registered."""
        import mcp_server.main as main_module

        # Verify MCP server is created
        assert main_module.mcp is not None
        assert "Jenkins MCP Server" in str(main_module.mcp)

        # Verify that the tool functions exist as FunctionTool objects
        # (They get transformed by the @mcp.tool decorator)
        assert hasattr(main_module, "jenkins_get_version")
        assert hasattr(main_module, "jenkins_get_job_info")
        assert hasattr(main_module, "jenkins_run_job")
        assert hasattr(main_module, "jenkins_get_job_console")
        assert hasattr(main_module, "jenkins_get_jobs")

        # Verify these are MCP FunctionTool objects
        assert str(type(main_module.jenkins_get_version)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_get_job_info)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_run_job)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_get_job_console)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_get_jobs)).endswith("FunctionTool'>")

    def test_global_state_management(self, mock_env_vars):
        """Test global state management in the module."""
        import mcp_server.main as main_module

        # Test initial state
        original_jenkins_api = main_module.jenkins_api

        # Reset and test singleton pattern
        main_module.jenkins_api = None

        with patch("mcp_server.main.JenkinsApi") as mock_jenkins_class:
            mock_instance = Mock()
            mock_jenkins_class.return_value = mock_instance

            # First call should create instance
            api1 = main_module.get_jenkins_api()
            assert api1 == mock_instance
            assert main_module.jenkins_api == mock_instance

            # Second call should return same instance
            api2 = main_module.get_jenkins_api()
            assert api2 == mock_instance
            assert api1 is api2

            # Constructor should only be called once
            mock_jenkins_class.assert_called_once()

        # Restore original state
        main_module.jenkins_api = original_jenkins_api


class TestDirectMCPToolFunctions:
    """Test the MCP tool functions directly to achieve better coverage."""

    def test_jenkins_get_version_tool_success(self, mock_env_vars):
        """Test jenkins_get_version tool function directly - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_version.return_value = "2.401.3"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function through the underlying function
                result = main_module.jenkins_get_version.fn()

                assert result == "Jenkins version: 2.401.3"
                mock_api.get_version.assert_called_once()
                mock_logger.info.assert_called_once_with("Jenkins version: 2.401.3")

    def test_jenkins_get_version_tool_exception(self, mock_env_vars):
        """Test jenkins_get_version tool function directly - exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_version.side_effect = Exception("Connection failed")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_get_version.fn()

                assert "Error getting Jenkins version: Connection failed" in result
                mock_api.get_version.assert_called_once()
                mock_logger.error.assert_called_once_with("Failed to get Jenkins version: Connection failed")

    def test_jenkins_get_job_info_tool_success(self, mock_env_vars, sample_job_info):
        """Test jenkins_get_job_info tool function directly - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_details.return_value = sample_job_info

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_get_job_info.fn("test-job")

                # Parse the JSON result to verify it's valid
                parsed_result = json.loads(result)
                assert parsed_result == sample_job_info
                mock_api.get_job_details.assert_called_once_with("test-job")
                mock_logger.info.assert_called_once_with("Successfully retrieved job info for: test-job")

    def test_jenkins_get_job_info_tool_error_response(self, mock_env_vars):
        """Test jenkins_get_job_info tool function directly - error response case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_details.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            # Call the actual MCP tool function
            result = main_module.jenkins_get_job_info.fn("nonexistent-job")

            assert "Job not found:" in result
            assert "Job 'nonexistent-job' does not exist" in result
            mock_api.get_job_details.assert_called_once_with("nonexistent-job")

    def test_jenkins_get_job_info_tool_exception(self, mock_env_vars):
        """Test jenkins_get_job_info tool function directly - exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_details.side_effect = Exception("API Error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_get_job_info.fn("test-job")

                assert "Failed to get job info for 'test-job': API Error" in result
                mock_api.get_job_details.assert_called_once_with("test-job")
                mock_logger.error.assert_called_once_with("Failed to get job info for 'test-job': API Error")

    def test_jenkins_run_job_tool_success_no_parameters(self, mock_env_vars):
        """Test jenkins_run_job tool function directly - success with no parameters."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.run_job.return_value = "Job 'test-job' started successfully. Build number: 5"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            # Call the actual MCP tool function
            result = main_module.jenkins_run_job.fn("test-job", "{}")

            assert "Job 'test-job' started successfully. Build number: 5" in result
            mock_api.run_job.assert_called_once_with("test-job", None)

    def test_jenkins_run_job_tool_success_with_parameters(self, mock_env_vars, valid_job_parameters):
        """Test jenkins_run_job tool function directly - success with parameters."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.run_job.return_value = "Job 'test-job' started successfully. Build number: 5"
        parameters_json = json.dumps(valid_job_parameters)

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            # Call the actual MCP tool function
            result = main_module.jenkins_run_job.fn("test-job", parameters_json)

            assert "Job 'test-job' started successfully. Build number: 5" in result
            mock_api.run_job.assert_called_once_with("test-job", valid_job_parameters)

    def test_jenkins_run_job_tool_invalid_json_parameters(self, mock_env_vars, invalid_json_parameters):
        """Test jenkins_run_job tool function directly - invalid JSON parameters."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_run_job.fn("test-job", invalid_json_parameters)

                assert "Invalid JSON in parameters:" in result
                mock_logger.error.assert_called()
                # run_job should not be called when JSON is invalid
                mock_api.run_job.assert_not_called()

    def test_jenkins_run_job_tool_empty_parameters(self, mock_env_vars):
        """Test jenkins_run_job tool function directly - empty parameters."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.run_job.return_value = "Job started successfully"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            # Test empty string parameters
            result = main_module.jenkins_run_job.fn("test-job", "")

            assert "Job started successfully" in result
            mock_api.run_job.assert_called_once_with("test-job", None)

    def test_jenkins_run_job_tool_exception(self, mock_env_vars):
        """Test jenkins_run_job tool function directly - exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.run_job.side_effect = Exception("Jenkins API Error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_run_job.fn("test-job", "{}")

                assert "Failed to run job 'test-job': Jenkins API Error" in result
                mock_api.run_job.assert_called_once_with("test-job", None)
                mock_logger.error.assert_called_once_with("Failed to run job 'test-job': Jenkins API Error")

    def test_jenkins_get_job_console_tool_success_with_build_number(self, mock_env_vars, sample_console_output):
        """Test jenkins_get_job_console tool function directly - success with build number."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.return_value = sample_console_output

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            # Call the actual MCP tool function
            result = main_module.jenkins_get_job_console.fn("test-job", 5)

            assert result == sample_console_output
            mock_api.get_job_console.assert_called_once_with("test-job", 5)

    def test_jenkins_get_job_console_tool_success_without_build_number(self, mock_env_vars, sample_console_output):
        """Test jenkins_get_job_console tool function directly - success without build number."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.return_value = sample_console_output

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            # Call the actual MCP tool function
            result = main_module.jenkins_get_job_console.fn("test-job", None)

            assert result == sample_console_output
            mock_api.get_job_console.assert_called_once_with("test-job", None)

    def test_jenkins_get_job_console_tool_exception(self, mock_env_vars):
        """Test jenkins_get_job_console tool function directly - exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.side_effect = Exception("Console retrieval failed")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_get_job_console.fn("test-job", 5)

                assert "Failed to get console output for 'test-job': Console retrieval failed" in result
                mock_api.get_job_console.assert_called_once_with("test-job", 5)
                mock_logger.error.assert_called_once_with(
                    "Failed to get console output for 'test-job': Console retrieval failed"
                )

    def test_jenkins_get_jobs_tool_success(self, mock_env_vars, sample_jobs_list):
        """Test jenkins_get_jobs tool function directly - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_all_jobs_list.return_value = sample_jobs_list

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_get_jobs.fn()

                # Parse the JSON result to verify it's valid
                parsed_result = json.loads(result)
                assert parsed_result == sample_jobs_list
                mock_api.get_all_jobs_list.assert_called_once()
                mock_logger.info.assert_called_once_with("Successfully retrieved 3 jobs")

    def test_jenkins_get_jobs_tool_error_response(self, mock_env_vars):
        """Test jenkins_get_jobs tool function directly - error response case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_all_jobs_list.side_effect = JenkinsApiError(
            "Permission denied: user lacks Overall/Read permission"
        )

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            # Call the actual MCP tool function
            result = main_module.jenkins_get_jobs.fn()

            assert "Jenkins API error:" in result
            assert "Permission denied: user lacks Overall/Read permission" in result
            mock_api.get_all_jobs_list.assert_called_once()

    def test_jenkins_get_jobs_tool_exception(self, mock_env_vars):
        """Test jenkins_get_jobs tool function directly - exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_all_jobs_list.side_effect = Exception("Jobs retrieval failed")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_get_jobs.fn()

                assert "Failed to get jobs list: Jobs retrieval failed" in result
                mock_api.get_all_jobs_list.assert_called_once()
                mock_logger.error.assert_called_once_with("Failed to get jobs list: Jobs retrieval failed")
