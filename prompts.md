Enhance the existing testing framework for
  the RAG system in @backend/tests. the
  current test covers units component but are
  missing essential API testing
  infrastructure:
  - API endpoint test - Test the FAST API
  endpoints (/api/query, /api/courses, /) for
  proper request/response handling
  - pytest configuration - add
  pytest.ini_options in pyproject.toml for
  cleaner test execution 
   - test fixtures - create conftest.py with
  shared fixture for mocking and test data
  setup