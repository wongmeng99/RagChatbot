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

----------------------------------------------

/implement-feature Toggle button design
  - Create a toggle button that fits the existing design aesthetic
  - position it in the top-right
  - Use an icon based design (sun/moon icons or similar)
  - smooth transition animation when toggling
  - button should be accesible and keyboard-navigable
  ----------------------------
  /implement-feature add a light theme variant
  with appropriate colors.
  - light background colors
  - dark text for good contrast
  - adjusted primary and secondary colors
  - proper border and surface colors
  - maintain good accesibility standards
--------------------------------
  add and commit with a descriptive message

----------------------------------------------

Add essential code quality tools to the development workflow. set up
  black for automatic code formatting. Add proper formatting consistency
  throughout the codebase and  create development scripts for running
  quality checks.