 the chat interface displays qeury responses with source citations. i need to modify it so each source becomes a clicklable link that
  opens the corresponding lesson video in a tab:
  - when courses are processed into chunks @backend/document_processor.py  , the link of each lesson is stored in the course_catalog
  collection
  - modify _format_results in @backend/search_tools.py so that the lesson links are also returned
  - the links should be the embedded invisbly (no visible URL text)

---------------------------------------------
add a new "+ new chat" button to the left sidebar above the courses section, when clicked, it should:
-  clears the current conversation in the chat window
- start a new session without page reload
  - handle proper  cleanup on both @frontend/ and @backend/
  - match the styling of existing sections (courses, try asking)- same font size, color, and uppercase formatting

----------------------------------------------
using the playwright MCP server visit 127.0.0.1:8000 and view the new chat button. i want that button to look the same as the other
  links below for Courses and Try asking. Make sure this is left alligned and that the border is removed

----------------------------------------------
In @backend/search_tools.py , add a second tool along side the existing content-related tool. This new too should handle course
outline queries.
- Functionality:
   - input: Course title
   - output: course title, course link, and complete lesson lists
   - for each lesson: lesson number, lesson title
- Data source: course metadata collection of the vector store
- update the system prompt in @backend/ai_generator.py so that the course title, course link, the number and title of each lessons are
all returned to address an outline-relatd queries
- make sure the new tool is registered in the system.

---------------------------------------------

The RAG chatbot returns 'query failed' for any content-related questions.
I need you to:
1. write tests to evaluate the output of the execute method of the CourseSearchTool in @backend/search_tools.py
2. write tests to evaluate if @backend/ai_generator.py correctly calls for the course search tools
3. write tests to evaluate how the RAG system is handling the content-query related questions.

save the tests in a tests folder within @backend/. Run those tests against the current system to identify which components are
failing. Propose fixes based on what the tests reveal is broken.

think a lot