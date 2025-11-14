# TODO: Advanced Chatbot Integration for MasteringMarket

## Completed Tasks
- [x] Create `chatbot_intents.json`: JSON structure with intents for all 10 categories (General Introduction, Stock Market Basics, AI & Prediction Model, Stock-Specific Queries, Market Insights & News, Portfolio & Simulation Support, Learning & Gamification, Account & Tech Support, Mental Health & Motivation, Fun & Engagement). Include sample utterances and responses with placeholders for dynamic data.
- [x] Create `chatbot_logic.js`: Node.js module for intent matching (using keyword matching or compromise library), response generation, context handling, and API integration placeholders.
- [x] Create `Chatbot.jsx`: React component for the chat UI (ChatGPT-style, input box, auto-scroll, typing indicator).
- [x] Create `chatbot_api.js`: Examples for connecting to stock APIs (Yahoo Finance) and OpenAI API for advanced responses.
- [x] Create `advanced_chatbot.py`: New Streamlit page that embeds the React chatbot using `st.components.v1.html`.
- [x] Update `app.py`: Add the new advanced chatbot page to the navigation/sidebar menu under Chatbot.
- [x] Create/update `package.json`: Add JS dependencies (react, compromise, yahoo-finance2, openai, etc.).

## Followup Steps
- [x] Install JS dependencies (npm install).
- [x] Build the React component (npm run build).
- [x] Set up backend API endpoint for chatbot responses (Express.js server running on port 3001).
- [x] Test chatbot logic with sample queries.
- [x] Test embedding in Streamlit (app running at http://localhost:8503).
- [x] Remove basic stock chatbot and add search bar to advanced chatbot.
- [ ] Ensure seamless integration with existing app.
- [ ] Verify fallback responses and dynamic data handling.
- [ ] Add environment variables for API keys (OpenAI, etc.).
