from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sympy import symbols, expand, factor, latex
import random
from routes.auth import get_current_user

router = APIRouter(prefix="/api/generate-question", tags=["question-generator"])

class GenerateQuestionRequest(BaseModel):
    difficulty: str  # "easy", "medium", "hard"

@router.post("/", response_model=dict)
async def generate_question(request: GenerateQuestionRequest, current_user: dict = Depends(get_current_user)):
    x = symbols('x')
    difficulty = request.difficulty.lower()

    if difficulty == "easy":
        # Easy: x^2 + bx + c
        root1 = random.randint(-5, 5)
        root2 = random.randint(-5, 5)
        poly = expand((x - root1) * (x - root2))
        factored = factor(poly)

    elif difficulty == "medium":
        # Medium: ax^2 + bx + c, a ≠ 1
        a = random.randint(2, 5)
        root1 = random.randint(-5, 5)
        root2 = random.randint(-5, 5)
        poly = expand(a * (x - root1) * (x - root2))
        factored = factor(poly)

    elif difficulty == "hard":
        # Hard: Cubic polynomial
        root1 = random.randint(-3, 3)
        p = random.randint(-5, 5)
        q = random.randint(-5, 5)
        poly = expand((x - root1) * (x**2 + p*x + q))
        factored = factor(poly)

    else:
        raise HTTPException(status_code=400, detail="Invalid difficulty level")

    # Convert to LaTeX
    question_latex = f"\\text{{Factor the polynomial: }} {latex(poly)}"
    answer_latex = latex(factored)

    return {
        "question": question_latex,
        "correctAnswer": answer_latex,
    }
