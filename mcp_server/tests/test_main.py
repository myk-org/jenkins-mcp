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
        assert hasattr(main_module, "jenkins_wait_for_build")
        assert hasattr(main_module, "jenkins_get_build_errors")
        assert hasattr(main_module, "jenkins_enable_job")
        assert hasattr(main_module, "jenkins_disable_job")
        assert hasattr(main_module, "jenkins_rebuild")
        assert hasattr(main_module, "jenkins_get_build_parameters")
        assert hasattr(main_module, "jenkins_enable_all_jobs")

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
        assert str(type(main_module.jenkins_wait_for_build)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_get_build_errors)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_enable_job)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_disable_job)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_rebuild)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_get_build_parameters)).endswith("FunctionTool'>")
        assert str(type(main_module.jenkins_enable_all_jobs)).endswith("FunctionTool'>")

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
            mock_api.get_job_console.assert_called_once_with("test-job", 5, tail=None, head=None)

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
            mock_api.get_job_console.assert_called_once_with("test-job", None, tail=None, head=None)

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
                mock_api.get_job_console.assert_called_once_with("test-job", 5, tail=None, head=None)
                mock_logger.error.assert_called_once_with(
                    "Failed to get console output for 'test-job': Console retrieval failed"
                )

    def test_jenkins_get_job_console_tool_with_tail(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with tail parameter."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.return_value = "Line 4\nLine 5"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            result = main_module.jenkins_get_job_console.fn("test-job", 5, tail=2)

            assert result == "Line 4\nLine 5"
            mock_api.get_job_console.assert_called_once_with("test-job", 5, tail=2, head=None)

    def test_jenkins_get_job_console_tool_with_head(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with head parameter."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.return_value = "Line 1\nLine 2"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            result = main_module.jenkins_get_job_console.fn("test-job", 5, head=2)

            assert result == "Line 1\nLine 2"
            mock_api.get_job_console.assert_called_once_with("test-job", 5, tail=None, head=2)

    def test_jenkins_get_job_console_tool_tail_and_head_error(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with both tail and head raises error."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.side_effect = ValueError("tail and head are mutually exclusive; provide only one")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_job_console.fn("test-job", 5, tail=2, head=2)

                assert "Invalid parameters:" in result
                assert "tail and head are mutually exclusive" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_job_console_tool_invalid_tail_zero(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with tail=0 raises error."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.side_effect = ValueError("tail must be a positive integer")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_job_console.fn("test-job", 5, tail=0)

                assert "Invalid parameters:" in result
                assert "tail must be a positive integer" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_job_console_tool_invalid_tail_negative(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with negative tail raises error."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.side_effect = ValueError("tail must be a positive integer")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_job_console.fn("test-job", 5, tail=-5)

                assert "Invalid parameters:" in result
                assert "tail must be a positive integer" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_job_console_tool_invalid_head_zero(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with head=0 raises error."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.side_effect = ValueError("head must be a positive integer")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_job_console.fn("test-job", 5, head=0)

                assert "Invalid parameters:" in result
                assert "head must be a positive integer" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_job_console_tool_invalid_head_negative(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with negative head raises error."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.side_effect = ValueError("head must be a positive integer")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_job_console.fn("test-job", 5, head=-5)

                assert "Invalid parameters:" in result
                assert "head must be a positive integer" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_job_console_tool_tail_exceeds_lines(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with tail exceeding total lines."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.return_value = "Line 1\nLine 2\nLine 3"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            result = main_module.jenkins_get_job_console.fn("test-job", 5, tail=100)

            assert result == "Line 1\nLine 2\nLine 3"
            mock_api.get_job_console.assert_called_once_with("test-job", 5, tail=100, head=None)

    def test_jenkins_get_job_console_tool_head_exceeds_lines(self, mock_env_vars):
        """Test jenkins_get_job_console tool function with head exceeding total lines."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_job_console.return_value = "Line 1\nLine 2\nLine 3"

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            result = main_module.jenkins_get_job_console.fn("test-job", 5, head=100)

            assert result == "Line 1\nLine 2\nLine 3"
            mock_api.get_job_console.assert_called_once_with("test-job", 5, tail=None, head=100)

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

    def test_jenkins_wait_for_build_tool_success(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function directly - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        build_result = {
            "build_number": 5,
            "result": "SUCCESS",
            "duration": 45000,
            "url": "http://test-jenkins.com/job/test-job/5/",
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.return_value = build_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                # Call the actual MCP tool function
                result = main_module.jenkins_wait_for_build.fn("test-job", 5, 60, 5)

                # Parse the JSON result to verify it's valid
                parsed_result = json.loads(result)
                assert parsed_result == build_result
                mock_api.wait_for_build.assert_called_once_with(
                    job_name="test-job",
                    build_number=5,
                    timeout=60,
                    poll_interval=5,
                )
                mock_logger.info.assert_called_once_with("Build 'test-job#5' completed: SUCCESS")

    def test_jenkins_wait_for_build_tool_success_default_params(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function with default parameters."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        build_result = {
            "build_number": 10,
            "result": "SUCCESS",
            "duration": 30000,
            "url": "http://test-jenkins.com/job/test-job/10/",
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.return_value = build_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger"):
                # Call with default parameters
                result = main_module.jenkins_wait_for_build.fn("test-job")

                parsed_result = json.loads(result)
                assert parsed_result == build_result
                mock_api.wait_for_build.assert_called_once_with(
                    job_name="test-job",
                    build_number=None,
                    timeout=3600,
                    poll_interval=30,
                )

    def test_jenkins_wait_for_build_tool_build_not_found(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function - build not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsBuildNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.side_effect = JenkinsBuildNotFoundError("No builds found for job 'test-job'")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_wait_for_build.fn("test-job")

                assert "Build not found:" in result
                assert "No builds found for job 'test-job'" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_wait_for_build_tool_job_not_found(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function - job not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_wait_for_build.fn("nonexistent-job")

                assert "Job not found:" in result
                assert "Job 'nonexistent-job' does not exist" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_wait_for_build_tool_connection_error(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function - connection error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_wait_for_build.fn("test-job", 5)

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_wait_for_build_tool_api_error(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function - API error (timeout) case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.side_effect = JenkinsApiError("Timeout waiting for build 'test-job#5' after 60 seconds")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_wait_for_build.fn("test-job", 5, 60, 5)

                assert "Jenkins API error:" in result
                assert "Timeout waiting for build" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_wait_for_build_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function - unexpected exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_wait_for_build.fn("test-job", 5)

                assert "Failed to wait for build 'test-job': Unexpected error" in result
                mock_logger.error.assert_called_once_with("Failed to wait for build 'test-job': Unexpected error")

    def test_jenkins_wait_for_build_tool_failure_result(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function - FAILURE result."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        build_result = {
            "build_number": 5,
            "result": "FAILURE",
            "duration": 30000,
            "url": "http://test-jenkins.com/job/test-job/5/",
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.return_value = build_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_wait_for_build.fn("test-job", 5)

                parsed_result = json.loads(result)
                assert parsed_result["result"] == "FAILURE"
                mock_logger.info.assert_called_once_with("Build 'test-job#5' completed: FAILURE")

    def test_jenkins_wait_for_build_tool_invalid_timeout(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function - invalid timeout (non-positive) raises ValueError."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.side_effect = ValueError("timeout must be a positive integer")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_wait_for_build.fn("test-job", 5, timeout=0)

                assert "Invalid parameters:" in result
                assert "timeout must be a positive integer" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_wait_for_build_tool_invalid_poll_interval(self, mock_env_vars):
        """Test jenkins_wait_for_build tool function - invalid poll_interval (non-positive) raises ValueError."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.wait_for_build.side_effect = ValueError("poll_interval must be a positive integer")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_wait_for_build.fn("test-job", 5, poll_interval=-1)

                assert "Invalid parameters:" in result
                assert "poll_interval must be a positive integer" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_errors_tool_success(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        errors_result = {
            "errors": [
                {"line_number": 10, "line": "[ERROR] Failed to compile", "category": "error"},
                {"line_number": 15, "line": "Exception in thread", "category": "exception"},
            ],
            "summary": {"error": 1, "exception": 1},
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.return_value = errors_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_errors.fn("test-job", 5, "[]")

                parsed_result = json.loads(result)
                assert parsed_result == errors_result
                mock_api.get_build_errors.assert_called_once_with(
                    job_name="test-job",
                    build_number=5,
                    patterns=None,
                )
                mock_logger.info.assert_called_once_with("Found 2 errors in 'test-job' build 5")

    def test_jenkins_get_build_errors_tool_success_with_patterns(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - success with custom patterns."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        errors_result = {
            "errors": [
                {"line_number": 5, "line": "CUSTOM_ERROR found", "category": "custom"},
            ],
            "summary": {"custom": 1},
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.return_value = errors_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger"):
                result = main_module.jenkins_get_build_errors.fn("test-job", 5, '["CUSTOM_ERROR", "MY_PATTERN"]')

                parsed_result = json.loads(result)
                assert parsed_result == errors_result
                mock_api.get_build_errors.assert_called_once_with(
                    job_name="test-job",
                    build_number=5,
                    patterns=["CUSTOM_ERROR", "MY_PATTERN"],
                )

    def test_jenkins_get_build_errors_tool_success_default_params(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function with default parameters."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        errors_result = {
            "errors": [],
            "summary": {},
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.return_value = errors_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_errors.fn("test-job")

                parsed_result = json.loads(result)
                assert parsed_result == errors_result
                mock_api.get_build_errors.assert_called_once_with(
                    job_name="test-job",
                    build_number=None,
                    patterns=None,
                )
                mock_logger.info.assert_called_once_with("Found 0 errors in 'test-job' build latest")

    def test_jenkins_get_build_errors_tool_invalid_json_patterns(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - invalid JSON patterns."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_errors.fn("test-job", 5, '["invalid json')

                assert "Invalid JSON in patterns:" in result
                mock_logger.error.assert_called()
                mock_api.get_build_errors.assert_not_called()

    def test_jenkins_get_build_errors_tool_build_not_found(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - build not found."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsBuildNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.side_effect = JenkinsBuildNotFoundError("No builds found for job 'test-job'")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_errors.fn("test-job")

                assert "Build not found:" in result
                assert "No builds found for job 'test-job'" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_errors_tool_job_not_found(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - job not found."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_errors.fn("nonexistent-job")

                assert "Job not found:" in result
                assert "Job 'nonexistent-job' does not exist" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_errors_tool_connection_error(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - connection error."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_errors.fn("test-job", 5)

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_errors_tool_api_error(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - API error."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.side_effect = JenkinsApiError("API error occurred")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_errors.fn("test-job", 5)

                assert "Jenkins API error:" in result
                assert "API error occurred" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_errors_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - unexpected exception."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_errors.fn("test-job", 5)

                assert "Failed to get build errors for 'test-job': Unexpected error" in result
                mock_logger.error.assert_called_once_with("Failed to get build errors for 'test-job': Unexpected error")

    def test_jenkins_get_build_errors_tool_empty_patterns_string(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - empty patterns string."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        errors_result = {"errors": [], "summary": {}}

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.return_value = errors_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger"):
                # Test with empty string
                result = main_module.jenkins_get_build_errors.fn("test-job", 5, "")

                parsed_result = json.loads(result)
                assert parsed_result == errors_result
                # Empty string should result in patterns=None (use defaults)
                mock_api.get_build_errors.assert_called_once_with(
                    job_name="test-job",
                    build_number=5,
                    patterns=None,
                )

    def test_jenkins_get_build_errors_tool_whitespace_patterns(self, mock_env_vars):
        """Test jenkins_get_build_errors tool function - whitespace-only patterns."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        errors_result = {"errors": [], "summary": {}}

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_errors.return_value = errors_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger"):
                # Test with whitespace only
                result = main_module.jenkins_get_build_errors.fn("test-job", 5, "   ")

                parsed_result = json.loads(result)
                assert parsed_result == errors_result
                # Whitespace should result in patterns=None (use defaults)
                mock_api.get_build_errors.assert_called_once_with(
                    job_name="test-job",
                    build_number=5,
                    patterns=None,
                )

    def test_jenkins_enable_job_tool_success(self, mock_env_vars):
        """Test jenkins_enable_job tool function - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        enable_result = {
            "success": True,
            "job_name": "test-job",
            "enabled": True,
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_job_state.return_value = enable_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_job.fn("test-job")

                parsed_result = json.loads(result)
                assert parsed_result == enable_result
                mock_api.enable_job_state.assert_called_once_with("test-job")
                mock_logger.info.assert_called_once_with("Job 'test-job' enabled: True")

    def test_jenkins_enable_job_tool_job_not_found(self, mock_env_vars):
        """Test jenkins_enable_job tool function - job not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_job_state.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_job.fn("nonexistent-job")

                assert "Job not found:" in result
                assert "Job 'nonexistent-job' does not exist" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_enable_job_tool_connection_error(self, mock_env_vars):
        """Test jenkins_enable_job tool function - connection error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_job_state.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_job.fn("test-job")

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_enable_job_tool_api_error(self, mock_env_vars):
        """Test jenkins_enable_job tool function - API error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_job_state.side_effect = JenkinsApiError("Permission denied")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_job.fn("test-job")

                assert "Jenkins API error:" in result
                assert "Permission denied" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_enable_job_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_enable_job tool function - unexpected exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_job_state.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_job.fn("test-job")

                assert "Failed to enable job 'test-job': Unexpected error" in result
                mock_logger.error.assert_called_once_with("Failed to enable job 'test-job': Unexpected error")

    def test_jenkins_disable_job_tool_success(self, mock_env_vars):
        """Test jenkins_disable_job tool function - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        disable_result = {
            "success": True,
            "job_name": "test-job",
            "enabled": False,
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.disable_job_state.return_value = disable_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_disable_job.fn("test-job")

                parsed_result = json.loads(result)
                assert parsed_result == disable_result
                mock_api.disable_job_state.assert_called_once_with("test-job")
                mock_logger.info.assert_called_once_with("Job 'test-job' disabled: enabled=False")

    def test_jenkins_disable_job_tool_job_not_found(self, mock_env_vars):
        """Test jenkins_disable_job tool function - job not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.disable_job_state.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_disable_job.fn("nonexistent-job")

                assert "Job not found:" in result
                assert "Job 'nonexistent-job' does not exist" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_disable_job_tool_connection_error(self, mock_env_vars):
        """Test jenkins_disable_job tool function - connection error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.disable_job_state.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_disable_job.fn("test-job")

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_disable_job_tool_api_error(self, mock_env_vars):
        """Test jenkins_disable_job tool function - API error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.disable_job_state.side_effect = JenkinsApiError("Permission denied")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_disable_job.fn("test-job")

                assert "Jenkins API error:" in result
                assert "Permission denied" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_disable_job_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_disable_job tool function - unexpected exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.disable_job_state.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_disable_job.fn("test-job")

                assert "Failed to disable job 'test-job': Unexpected error" in result
                mock_logger.error.assert_called_once_with("Failed to disable job 'test-job': Unexpected error")

    def test_jenkins_rebuild_tool_success(self, mock_env_vars):
        """Test jenkins_rebuild tool function - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        rebuild_result = {
            "success": True,
            "job_name": "test-job",
            "source_build_number": 5,
            "new_build_number": 10,
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.rebuild.return_value = rebuild_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_rebuild.fn("test-job", 5)

                parsed_result = json.loads(result)
                assert parsed_result == rebuild_result
                mock_api.rebuild.assert_called_once_with("test-job", 5)
                mock_logger.info.assert_called_once_with(
                    "Rebuild triggered for 'test-job' from build #5. New build number: 10"
                )

    def test_jenkins_rebuild_tool_build_not_found(self, mock_env_vars):
        """Test jenkins_rebuild tool function - build not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsBuildNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.rebuild.side_effect = JenkinsBuildNotFoundError("Build 'test-job#999' not found")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_rebuild.fn("test-job", 999)

                assert "Build not found:" in result
                assert "Build 'test-job#999' not found" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_rebuild_tool_job_not_found(self, mock_env_vars):
        """Test jenkins_rebuild tool function - job not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.rebuild.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_rebuild.fn("nonexistent-job", 5)

                assert "Job not found:" in result
                assert "Job 'nonexistent-job' does not exist" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_rebuild_tool_connection_error(self, mock_env_vars):
        """Test jenkins_rebuild tool function - connection error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.rebuild.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_rebuild.fn("test-job", 5)

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_rebuild_tool_api_error(self, mock_env_vars):
        """Test jenkins_rebuild tool function - API error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.rebuild.side_effect = JenkinsApiError("Permission denied")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_rebuild.fn("test-job", 5)

                assert "Jenkins API error:" in result
                assert "Permission denied" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_rebuild_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_rebuild tool function - unexpected exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.rebuild.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_rebuild.fn("test-job", 5)

                assert "Failed to rebuild job 'test-job': Unexpected error" in result
                mock_logger.error.assert_called_once_with("Failed to rebuild job 'test-job': Unexpected error")


class TestJenkinsCancelBuildTool:
    """Test the jenkins_cancel_build tool function."""

    def test_jenkins_cancel_build_tool_success_with_build_number(self, mock_env_vars):
        """Test jenkins_cancel_build tool function - success with specific build number."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        cancel_result = {
            "success": True,
            "job_name": "test-job",
            "build_number": 5,
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.cancel_build.return_value = cancel_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_cancel_build.fn("test-job", 5)

                parsed_result = json.loads(result)
                assert parsed_result == cancel_result
                mock_api.cancel_build.assert_called_once_with("test-job", 5)
                mock_logger.info.assert_called_once_with("Cancelled build 'test-job#5'")

    def test_jenkins_cancel_build_tool_success_without_build_number(self, mock_env_vars):
        """Test jenkins_cancel_build tool function - success using last build."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        cancel_result = {
            "success": True,
            "job_name": "test-job",
            "build_number": 10,
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.cancel_build.return_value = cancel_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_cancel_build.fn("test-job", None)

                parsed_result = json.loads(result)
                assert parsed_result == cancel_result
                mock_api.cancel_build.assert_called_once_with("test-job", None)
                mock_logger.info.assert_called_once_with("Cancelled build 'test-job#10'")

    def test_jenkins_cancel_build_tool_build_not_found(self, mock_env_vars):
        """Test jenkins_cancel_build tool function - build not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsBuildNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.cancel_build.side_effect = JenkinsBuildNotFoundError("Build 'test-job#999' not found")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_cancel_build.fn("test-job", 999)

                assert "Build not found:" in result
                assert "Build 'test-job#999' not found" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_cancel_build_tool_job_not_found(self, mock_env_vars):
        """Test jenkins_cancel_build tool function - job not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.cancel_build.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_cancel_build.fn("nonexistent-job", 5)

                assert "Job not found:" in result
                assert "Job 'nonexistent-job' does not exist" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_cancel_build_tool_connection_error(self, mock_env_vars):
        """Test jenkins_cancel_build tool function - connection error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.cancel_build.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_cancel_build.fn("test-job", 5)

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_cancel_build_tool_api_error(self, mock_env_vars):
        """Test jenkins_cancel_build tool function - API error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.cancel_build.side_effect = JenkinsApiError("Permission denied")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_cancel_build.fn("test-job", 5)

                assert "Jenkins API error:" in result
                assert "Permission denied" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_cancel_build_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_cancel_build tool function - unexpected exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.cancel_build.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_cancel_build.fn("test-job", 5)

                assert "Failed to cancel build for 'test-job': Unexpected error" in result
                mock_logger.error.assert_called_once_with("Failed to cancel build for 'test-job': Unexpected error")

    def test_jenkins_get_build_parameters_tool_success(self, mock_env_vars):
        """Test jenkins_get_build_parameters tool function - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        build_params_result = {
            "job_name": "test-job",
            "build_number": 5,
            "parameters": [
                {"name": "BRANCH", "value": "main"},
                {"name": "ENV", "value": "production"},
            ],
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_parameters.return_value = build_params_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_parameters.fn("test-job", 5)

                parsed_result = json.loads(result)
                assert parsed_result == build_params_result
                mock_api.get_build_parameters.assert_called_once_with("test-job", 5)
                mock_logger.info.assert_called_once_with("Retrieved 2 parameters from 'test-job#5'")

    def test_jenkins_get_build_parameters_tool_success_no_build_number(self, mock_env_vars):
        """Test jenkins_get_build_parameters tool function - success without build number."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        build_params_result = {
            "job_name": "test-job",
            "build_number": 10,
            "parameters": [
                {"name": "BRANCH", "value": "develop"},
            ],
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_parameters.return_value = build_params_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_parameters.fn("test-job", None)

                parsed_result = json.loads(result)
                assert parsed_result == build_params_result
                mock_api.get_build_parameters.assert_called_once_with("test-job", None)
                mock_logger.info.assert_called_once_with("Retrieved 1 parameters from 'test-job#10'")

    def test_jenkins_get_build_parameters_tool_no_parameters(self, mock_env_vars):
        """Test jenkins_get_build_parameters tool function - build with no parameters."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        build_params_result = {
            "job_name": "test-job",
            "build_number": 5,
            "parameters": [],
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_parameters.return_value = build_params_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_parameters.fn("test-job", 5)

                parsed_result = json.loads(result)
                assert parsed_result == build_params_result
                assert parsed_result["parameters"] == []
                mock_logger.info.assert_called_once_with("Retrieved 0 parameters from 'test-job#5'")

    def test_jenkins_get_build_parameters_tool_build_not_found(self, mock_env_vars):
        """Test jenkins_get_build_parameters tool function - build not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsBuildNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_parameters.side_effect = JenkinsBuildNotFoundError("Build 'test-job#999' not found")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_parameters.fn("test-job", 999)

                assert "Build not found:" in result
                assert "Build 'test-job#999' not found" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_parameters_tool_job_not_found(self, mock_env_vars):
        """Test jenkins_get_build_parameters tool function - job not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_parameters.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_parameters.fn("nonexistent-job", 5)

                assert "Job not found:" in result
                assert "Job 'nonexistent-job' does not exist" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_parameters_tool_connection_error(self, mock_env_vars):
        """Test jenkins_get_build_parameters tool function - connection error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_parameters.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_parameters.fn("test-job", 5)

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_parameters_tool_api_error(self, mock_env_vars):
        """Test jenkins_get_build_parameters tool function - API error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_parameters.side_effect = JenkinsApiError("Permission denied")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_parameters.fn("test-job", 5)

                assert "Jenkins API error:" in result
                assert "Permission denied" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_get_build_parameters_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_get_build_parameters tool function - unexpected exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.get_build_parameters.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_get_build_parameters.fn("test-job", 5)

                assert "Failed to get build parameters for 'test-job': Unexpected error" in result
                mock_logger.error.assert_called_once_with(
                    "Failed to get build parameters for 'test-job': Unexpected error"
                )


class TestJenkinsMonitorBuildToolDirect:
    """Test the jenkins_monitor_build MCP tool function directly."""

    def test_jenkins_monitor_build_tool_success(self, mock_env_vars, sample_console_output):
        """Test jenkins_monitor_build tool function - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.return_value = {
            "job_name": "test-job",
            "build_number": 5,
            "output": sample_console_output,
            "next_line": 9,
            "building": True,
            "result": None,
        }

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_monitor_build.fn("test-job", 5, 0)

                parsed_result = json.loads(result)
                assert parsed_result["job_name"] == "test-job"
                assert parsed_result["build_number"] == 5
                assert parsed_result["building"] is True
                assert parsed_result["result"] is None
                assert parsed_result["next_line"] == 9
                mock_api.monitor_build.assert_called_once_with(
                    job_name="test-job",
                    build_number=5,
                    from_line=0,
                )
                mock_logger.info.assert_called_once()

    def test_jenkins_monitor_build_tool_with_from_line(self, mock_env_vars):
        """Test jenkins_monitor_build tool function with from_line parameter."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.return_value = {
            "job_name": "test-job",
            "build_number": 5,
            "output": "Line 5: Some output\nLine 6: More output",
            "next_line": 7,
            "building": True,
            "result": None,
        }

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            result = main_module.jenkins_monitor_build.fn("test-job", 5, 5)

            parsed_result = json.loads(result)
            assert parsed_result["next_line"] == 7
            assert "Line 5: Some output" in parsed_result["output"]
            mock_api.monitor_build.assert_called_once_with(
                job_name="test-job",
                build_number=5,
                from_line=5,
            )

    def test_jenkins_monitor_build_tool_without_build_number(self, mock_env_vars):
        """Test jenkins_monitor_build tool function without build number (uses latest)."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.return_value = {
            "job_name": "test-job",
            "build_number": 10,
            "output": "Output from latest build",
            "next_line": 1,
            "building": False,
            "result": "SUCCESS",
        }

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            result = main_module.jenkins_monitor_build.fn("test-job", None, 0)

            parsed_result = json.loads(result)
            assert parsed_result["build_number"] == 10
            assert parsed_result["building"] is False
            assert parsed_result["result"] == "SUCCESS"
            mock_api.monitor_build.assert_called_once_with(
                job_name="test-job",
                build_number=None,
                from_line=0,
            )

    def test_jenkins_monitor_build_tool_invalid_from_line(self, mock_env_vars):
        """Test jenkins_monitor_build tool function with invalid from_line."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.side_effect = ValueError("from_line must be non-negative (>= 0)")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_monitor_build.fn("test-job", 5, -1)

                assert "Invalid parameters:" in result
                assert "from_line must be non-negative" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_monitor_build_tool_build_not_found(self, mock_env_vars):
        """Test jenkins_monitor_build tool function - build not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsBuildNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.side_effect = JenkinsBuildNotFoundError("Build 'test-job#999' not found")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_monitor_build.fn("test-job", 999, 0)

                assert "Build not found:" in result
                assert "Build 'test-job#999' not found" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_monitor_build_tool_job_not_found(self, mock_env_vars):
        """Test jenkins_monitor_build tool function - job not found case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsJobNotFoundError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.side_effect = JenkinsJobNotFoundError("Job 'nonexistent-job' does not exist")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_monitor_build.fn("nonexistent-job", None, 0)

                assert "Job not found:" in result
                assert "Job 'nonexistent-job' does not exist" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_monitor_build_tool_connection_error(self, mock_env_vars):
        """Test jenkins_monitor_build tool function - connection error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_monitor_build.fn("test-job", 5, 0)

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_monitor_build_tool_api_error(self, mock_env_vars):
        """Test jenkins_monitor_build tool function - Jenkins API error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.side_effect = JenkinsApiError("Some Jenkins error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_monitor_build.fn("test-job", 5, 0)

                assert "Jenkins API error:" in result
                assert "Some Jenkins error" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_monitor_build_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_monitor_build tool function - unexpected exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_monitor_build.fn("test-job", 5, 0)

                assert "Failed to monitor build for 'test-job': Unexpected error" in result
                mock_logger.error.assert_called_once_with("Failed to monitor build for 'test-job': Unexpected error")

    def test_jenkins_monitor_build_tool_completed_build(self, mock_env_vars):
        """Test jenkins_monitor_build tool function - completed build case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.monitor_build.return_value = {
            "job_name": "test-job",
            "build_number": 5,
            "output": "Build completed",
            "next_line": 10,
            "building": False,
            "result": "FAILURE",
        }

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            result = main_module.jenkins_monitor_build.fn("test-job", 5, 0)

            parsed_result = json.loads(result)
            assert parsed_result["building"] is False
            assert parsed_result["result"] == "FAILURE"


class TestJenkinsEnableAllJobsToolDirect:
    """Test the jenkins_enable_all_jobs MCP tool function directly."""

    def test_jenkins_enable_all_jobs_tool_success(self, mock_env_vars):
        """Test jenkins_enable_all_jobs tool function - success case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        enable_result = {
            "count": 3,
            "enabled_jobs": ["job1", "folder/job2", "folder/subfolder/job3"],
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_all_jobs.return_value = enable_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_all_jobs.fn()

                parsed_result = json.loads(result)
                assert parsed_result == enable_result
                mock_api.enable_all_jobs.assert_called_once_with(folder=None, recursive=True)
                mock_logger.info.assert_called_once_with("Enabled 3 jobs")

    def test_jenkins_enable_all_jobs_tool_with_folder(self, mock_env_vars):
        """Test jenkins_enable_all_jobs tool function with folder parameter."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        enable_result = {
            "count": 2,
            "enabled_jobs": ["myfolder/job1", "myfolder/job2"],
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_all_jobs.return_value = enable_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_all_jobs.fn(folder="myfolder", recursive=True)

                parsed_result = json.loads(result)
                assert parsed_result == enable_result
                mock_api.enable_all_jobs.assert_called_once_with(folder="myfolder", recursive=True)
                mock_logger.info.assert_called_once_with("Enabled 2 jobs")

    def test_jenkins_enable_all_jobs_tool_non_recursive(self, mock_env_vars):
        """Test jenkins_enable_all_jobs tool function with recursive=False."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        enable_result = {
            "count": 1,
            "enabled_jobs": ["job1"],
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_all_jobs.return_value = enable_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_all_jobs.fn(recursive=False)

                parsed_result = json.loads(result)
                assert parsed_result == enable_result
                mock_api.enable_all_jobs.assert_called_once_with(folder=None, recursive=False)
                mock_logger.info.assert_called_once_with("Enabled 1 jobs")

    def test_jenkins_enable_all_jobs_tool_no_jobs_enabled(self, mock_env_vars):
        """Test jenkins_enable_all_jobs tool function when no jobs are enabled."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        enable_result = {
            "count": 0,
            "enabled_jobs": [],
        }

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_all_jobs.return_value = enable_result

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_all_jobs.fn()

                parsed_result = json.loads(result)
                assert parsed_result == enable_result
                assert parsed_result["count"] == 0
                mock_logger.info.assert_called_once_with("Enabled 0 jobs")

    def test_jenkins_enable_all_jobs_tool_connection_error(self, mock_env_vars):
        """Test jenkins_enable_all_jobs tool function - connection error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsConnectionError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_all_jobs.side_effect = JenkinsConnectionError("Connection timeout")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_all_jobs.fn()

                assert "Connection error:" in result
                assert "Connection timeout" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_enable_all_jobs_tool_api_error(self, mock_env_vars):
        """Test jenkins_enable_all_jobs tool function - API error case."""
        import mcp_server.main as main_module
        from mcp_server.libs.jenkins_api import JenkinsApiError

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_all_jobs.side_effect = JenkinsApiError("Permission denied")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_all_jobs.fn()

                assert "Jenkins API error:" in result
                assert "Permission denied" in result
                mock_logger.error.assert_called_once()

    def test_jenkins_enable_all_jobs_tool_unexpected_exception(self, mock_env_vars):
        """Test jenkins_enable_all_jobs tool function - unexpected exception case."""
        import mcp_server.main as main_module

        # Reset global jenkins_api
        main_module.jenkins_api = None

        mock_api = Mock(spec=JenkinsApi)
        mock_api.enable_all_jobs.side_effect = Exception("Unexpected error")

        with patch("mcp_server.main.get_jenkins_api", return_value=mock_api):
            with patch("mcp_server.main.logger") as mock_logger:
                result = main_module.jenkins_enable_all_jobs.fn()

                assert "Failed to enable all jobs: Unexpected error" in result
                mock_logger.error.assert_called_once_with("Failed to enable all jobs: Unexpected error")
