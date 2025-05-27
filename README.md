## Backend Setup
1. Navigate to `backend/`.
2. Create `.env` from `.env.sample` and set `MONGODB_URI`, `JWT_SECRET`, `XAI_API_KEY`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Start server: `uvicorn main:app --reload`.
5. Access Swagger UI at `http://localhost:8000/docs`.

**Features**:
- MongoDB storage for users, questions, assignments, answers, classrooms.
- JWT authentication.
- xAI Grok API for answer evaluation and performance analysis.
- Manager-classroom assignments via `/api/managers/`.