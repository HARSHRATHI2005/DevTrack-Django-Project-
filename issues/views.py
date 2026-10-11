from pathlib import Path
from django.shortcuts import render
import json
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (Reporter, Issue, CriticalIssue, ALLOWED_STATUSES, ALLOWED_PRIORITIES , LowPriorityIssue)
# Create your views here.

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTERS_FILE = DATA_DIR / "reporters.json"
ISSUES_FILE = DATA_DIR / "issues.json"

def read_json(path):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_text("[]", encoding="utf-8")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def get_request_data(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Invalid JSON body")

    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")

    return data


def next_id(records):
    return max(
        (int(record["id"]) for record in records),
        default=0
    ) + 1


def parse_id(value):
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError("ID must be an integer")

    if result < 1:
        raise ValueError("ID must be positive")

    return result



class ReportersAPIView(APIView):

    def get(self, request):
        try:
            reporters = read_json(REPORTERS_FILE)

            reporter_id = request.query_params.get("id")

            if reporter_id is not None:
                reporter_id = parse_id(reporter_id)

                for reporter in reporters:
                    if int(reporter["id"]) == reporter_id:
                        return Response(
                            reporter,
                            status=status.HTTP_200_OK
                        )

                return Response(
                    {"error": "Reporter not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                reporters,
                status=status.HTTP_200_OK
            )

        except ValueError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def post(self, request):
        try:
            reporters = read_json(REPORTERS_FILE)
            data = request.data

            reporter_id = data.get("id")

            if reporter_id is None:
                reporter_id = next_id(reporters)
            else:
                reporter_id = parse_id(reporter_id)

            if any(
                int(r["id"]) == reporter_id for r in reporters
            ):
                return Response(
                    {"error": "Reporter ID already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            reporter = Reporter(
                reporter_id,
                data.get("name", ""),
                data.get("email", ""),
                data.get("team", "")
            )

            reporter.validate()
            result = reporter.to_dict()

            reporters.append(result)
            write_json(REPORTERS_FILE, reporters)

            return Response(
                result,
                status=status.HTTP_201_CREATED
            )

        except ValueError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )



class IssuesAPIView(APIView):

    def get(self, request):
        try:
            issues = read_json(ISSUES_FILE)

            issue_id = request.query_params.get("id")
            issue_status = request.query_params.get("status")

            if issue_id is not None:
                issue_id = parse_id(issue_id)

                for issue in issues:
                    if int(issue["id"]) == issue_id:
                        return Response(
                            issue,
                            status=status.HTTP_200_OK
                        )

                return Response(
                    {"error": "Issue not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            if issue_status is not None:
                if issue_status not in ALLOWED_STATUSES:
                    return Response(
                        {"error": "Invalid status"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                filtered_issues = [
                    issue for issue in issues
                    if issue["status"] == issue_status
                ]

                return Response(
                    filtered_issues,
                    status=status.HTTP_200_OK
                )

            return Response(
                issues,
                status=status.HTTP_200_OK
            )

        except ValueError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def post(self, request):
        try:
            issues = read_json(ISSUES_FILE)
            data = request.data

            reporter_id = parse_id(data.get("reporter_id"))
            reporters = read_json(REPORTERS_FILE)

            if not any(
                int(r["id"]) == reporter_id for r in reporters
            ):
                return Response(
                    {"error": "Reporter not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            issue_id = data.get("id")

            if issue_id is None:
                issue_id = next_id(issues)
            else:
                issue_id = parse_id(issue_id)

            if any(
                int(item["id"]) == issue_id for item in issues
            ):
                return Response(
                    {"error": "Issue ID already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            priority = data.get("priority", "medium")

            issue_data = {
                "id": issue_id,
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "status": data.get("status", "open"),
                "priority": priority,
                "reporter_id": reporter_id,
            }

            if priority == "critical":
                issue = CriticalIssue(**issue_data)
            elif priority == "low":
                issue = LowPriorityIssue(**issue_data)
            else:
                issue = Issue(**issue_data)

            issue.validate()

            response_data = issue.to_dict()
            response_data["message"] = issue.describe()

            issues.append(issue.to_dict())
            write_json(ISSUES_FILE, issues)

            return Response(
                response_data,
                status=status.HTTP_201_CREATED
            )

        except ValueError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
