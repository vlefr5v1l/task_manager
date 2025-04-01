"""
Utilities for parameterized testing.
Provides decorators and utilities to create more comprehensive tests.
"""
import copy
import re
from typing import List, Dict, Any, Callable, Union, Optional, Tuple

import pytest
from fastapi import HTTPException, status

from src.models.user import UserRole
from src.models.group import GroupRole
from src.models.task import TaskStatus, TaskPriority


# Helper for parameterized API tests
def api_test_cases(test_cases: List[Dict[str, Any]]) -> Callable:
    """
    Decorator to create parameterized API tests.
    Each test case is a dictionary with:
    - name: test case name
    - data: input data
    - expected_status: expected HTTP status code
    - expected_response: expected response data (can be partial)
    """

    def decorator(test_func: Callable) -> Callable:
        """Apply parameterization to the test function."""
        # Create meaningful test IDs based on test names
        ids = [case["name"] for case in test_cases]

        # Apply pytest parameterization
        return pytest.mark.parametrize("test_case", test_cases, ids=ids)(test_func)

    return decorator


# Helper for testing permission combinations
def permission_test_cases(
        endpoint: str,
        method: str = "get",
        roles: List[UserRole] = None,
        group_roles: List[GroupRole] = None,
        allowed_combinations: List[Tuple[UserRole, Optional[GroupRole]]] = None
) -> Callable:
    """
    Create test cases for various user role and group role combinations.

    Args:
        endpoint: API endpoint to test
        method: HTTP method to use (get, post, put, delete)
        roles: List of user roles to test
        group_roles: List of group roles to test
        allowed_combinations: List of (role, group_role) tuples that should be allowed

    Returns:
        Decorator function for parameterized tests
    """
    if roles is None:
        roles = list(UserRole)

    if group_roles is None:
        group_roles = list(GroupRole) + [None]  # Include not in group

    if allowed_combinations is None:
        # Default: only admin can access
        allowed_combinations = [(UserRole.ADMIN, None)]

    test_cases = []

    for role in roles:
        for group_role in group_roles:
            # Skip invalid combinations (e.g., ADMIN with group roles)
            if role == UserRole.ADMIN and group_role is not None:
                continue

            # Determine expected result
            is_allowed = (role, group_role) in allowed_combinations or role == UserRole.ADMIN
            expected_status = status.HTTP_201_CREATED if is_allowed else status.HTTP_403_FORBIDDEN

            test_cases.append({
                "name": f"{role.value}_{'no_group' if group_role is None else group_role.value}",
                "user_role": role,
                "group_role": group_role,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status
            })

    def decorator(test_func: Callable) -> Callable:
        """Apply parameterization to the test function."""
        # Create meaningful test IDs based on test names
        ids = [case["name"] for case in test_cases]

        # Apply pytest parameterization
        return pytest.mark.parametrize("permission_case", test_cases, ids=ids)(test_func)

    return decorator


# Examples of task data for different scenarios
def get_task_test_data() -> Dict[str, Dict[str, Any]]:
    """
    Get predefined task data for different test scenarios.
    """
    base_task = {
        "title": "Test Task",
        "description": "Test description",
        "status": TaskStatus.NEW.value,
        "priority": TaskPriority.MEDIUM.value,
        "project_id": 1
    }

    # Common error cases
    missing_title = copy.deepcopy(base_task)
    del missing_title["title"]

    missing_project = copy.deepcopy(base_task)
    del missing_project["project_id"]

    invalid_status = copy.deepcopy(base_task)
    invalid_status["status"] = "invalid_status"

    # Valid variations
    high_priority = copy.deepcopy(base_task)
    high_priority["priority"] = TaskPriority.HIGH.value
    high_priority["title"] = "High Priority Task"

    in_progress = copy.deepcopy(base_task)
    in_progress["status"] = TaskStatus.IN_PROGRESS.value
    in_progress["title"] = "In Progress Task"

    with_deadline = copy.deepcopy(base_task)
    with_deadline["deadline"] = "2024-12-31T23:59:59Z"
    with_deadline["title"] = "Task with Deadline"

    with_assignee = copy.deepcopy(base_task)
    with_assignee["assigned_to_id"] = 2
    with_assignee["title"] = "Assigned Task"

    return {
        "base": base_task,
        "missing_title": missing_title,
        "missing_project": missing_project,
        "invalid_status": invalid_status,
        "high_priority": high_priority,
        "in_progress": in_progress,
        "with_deadline": with_deadline,
        "with_assignee": with_assignee
    }


# API test case generator for task API
def task_api_test_cases() -> List[Dict[str, Any]]:
    """
    Generate test cases for task API endpoints.
    """
    task_data = get_task_test_data()

    test_cases = [
        {
            "name": "valid_task_creation",
            "endpoint": "/api/v1/tasks/",
            "method": "post",
            "data": task_data["base"],
            "expected_status": status.HTTP_201_CREATED,
            "expected_response": {"title": task_data["base"]["title"]}
        },
        {
            "name": "missing_title",
            "endpoint": "/api/v1/tasks/",
            "method": "post",
            "data": task_data["missing_title"],
            "expected_status": status.HTTP_422_UNPROCESSABLE_ENTITY
        },
        {
            "name": "missing_project",
            "endpoint": "/api/v1/tasks/",
            "method": "post",
            "data": task_data["missing_project"],
            "expected_status": status.HTTP_422_UNPROCESSABLE_ENTITY
        },
        {
            "name": "high_priority_task",
            "endpoint": "/api/v1/tasks/",
            "method": "post",
            "data": task_data["high_priority"],
            "expected_status": status.HTTP_201_CREATED,
            "expected_response": {"priority": TaskPriority.HIGH.value}
        },
        {
            "name": "in_progress_task",
            "endpoint": "/api/v1/tasks/",
            "method": "post",
            "data": task_data["in_progress"],
            "expected_status": status.HTTP_201_CREATED,
            "expected_response": {"status": TaskStatus.IN_PROGRESS.value}
        },
        {
            "name": "task_with_deadline",
            "endpoint": "/api/v1/tasks/",
            "method": "post",
            "data": task_data["with_deadline"],
            "expected_status": status.HTTP_201_CREATED,
            "expected_response": {"deadline": task_data["with_deadline"]["deadline"]}
        }
    ]

    return test_cases


# Example usage:
"""
@api_test_cases(task_api_test_cases())
async def test_task_api(async_client, db_session, test_case):
    # Set up any prerequisites

    # Get the method function from the client
    method_func = getattr(async_client, test_case["method"])

    # Make the request
    response = await method_func(
        test_case["endpoint"],
        json=test_case.get("data"),
        headers=headers
    )

    # Check status code
    assert response.status_code == test_case["expected_status"]

    # Check response data if expected
    if "expected_response" in test_case and response.status_code < 400:
        response_data = response.json()
        for key, value in test_case["expected_response"].items():
            assert response_data[key] == value
"""


# Helper to check exceptions
def assert_http_exception(expected_status: int, expected_detail: Optional[str] = None):
    """
    Context manager to assert that an HTTPException is raised with expected status and detail.

    Usage:
        with assert_http_exception(status.HTTP_403_FORBIDDEN, "Insufficient permissions"):
            await some_function_that_raises()
    """

    class HTTPExceptionAssertion:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Check that an exception was raised
            assert exc_type is not None, "Expected HTTPException but no exception was raised"

            # Check it's the right type
            assert issubclass(exc_type, HTTPException), f"Expected HTTPException but got {exc_type.__name__}"

            # Check status code
            assert exc_val.status_code == expected_status, \
                f"Expected status code {expected_status} but got {exc_val.status_code}"

            # Check detail if provided
            if expected_detail:
                if isinstance(expected_detail, str):
                    # Exact match
                    assert exc_val.detail == expected_detail, \
                        f"Expected detail '{expected_detail}' but got '{exc_val.detail}'"
                else:
                    # Regex pattern match
                    assert re.search(expected_detail, exc_val.detail), \
                        f"Detail '{exc_val.detail}' doesn't match pattern '{expected_detail}'"

            # Indicate that we've handled the exception
            return True

    return HTTPExceptionAssertion()