import json
import pytest
from datetime import date
from src.lambda_function import lambda_handler, SafariRequest

# Sample valid request data
VALID_REQUEST = {
    "travelDates": {
        "startDate": "2025-12-20",
        "endDate": "2025-12-27",
        "isFlexible": True
    },
    "group": {
        "international": {
            "adults": 2,
            "children": 1
        },
        "resident": {
            "adults": 0,
            "children": 0
        }
    },
    "accommodation": "Mid-range Lodge",
    "interests": [
        "Big Five wildlife sightings",
        "Photography",
        "Family-friendly"
    ],
    "travelStyle": "Some structure, some free time",
    "email": "user@example.com",
    "specialRequests": "We're celebrating a birthday and would love a surprise cake in the bush!"
}

def test_valid_request():
    """Test that a valid request returns a 200 status code and the same data"""
    response = lambda_handler(VALID_REQUEST, None)
    
    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    
    # Check that all fields are present and match
    assert response_body["travelDates"] == VALID_REQUEST["travelDates"]
    assert response_body["group"] == VALID_REQUEST["group"]
    assert response_body["accommodation"] == VALID_REQUEST["accommodation"]
    assert response_body["interests"] == VALID_REQUEST["interests"]
    assert response_body["travelStyle"] == VALID_REQUEST["travelStyle"]
    assert response_body["email"] == VALID_REQUEST["email"]
    assert response_body["specialRequests"] == VALID_REQUEST["specialRequests"]

def test_invalid_dates():
    """Test that invalid dates return a 400 status code"""
    invalid_request = VALID_REQUEST.copy()
    invalid_request["travelDates"]["startDate"] = "invalid-date"
    
    response = lambda_handler(invalid_request, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])

def test_negative_group_members():
    """Test that negative numbers for group members are rejected"""
    invalid_request = VALID_REQUEST.copy()
    invalid_request["group"]["international"]["adults"] = -1
    
    response = lambda_handler(invalid_request, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])

def test_missing_required_fields():
    """Test that missing required fields are rejected"""
    invalid_request = VALID_REQUEST.copy()
    del invalid_request["email"]
    
    response = lambda_handler(invalid_request, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])

def test_invalid_email_format():
    """Test that invalid email format is rejected"""
    invalid_request = VALID_REQUEST.copy()
    invalid_request["email"] = "invalid-email"
    
    response = lambda_handler(invalid_request, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])

def test_empty_interests():
    """Test that empty interests list is rejected"""
    invalid_request = VALID_REQUEST.copy()
    invalid_request["interests"] = []
    
    response = lambda_handler(invalid_request, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])

def test_cors_headers():
    """Test that CORS headers are present in the response"""
    response = lambda_handler(VALID_REQUEST, None)
    assert "headers" in response
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert response["headers"]["Content-Type"] == "application/json" 