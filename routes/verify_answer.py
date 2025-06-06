from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sympy import simplify, sympify
from sympy.parsing.latex import parse_latex
from sympy.core.sympify import SympifyError
from routes.auth import get_current_user
import re

router = APIRouter(prefix="/api/verify-answer", tags=["verify-answer"])

class VerifyAnswerRequest(BaseModel):
    questionType: str  # For future use
    correctAnswer: str  # LaTeX string
    testAnswer: str     # LaTeX string

@router.post("/", response_model=dict)
async def verify_answer(request: VerifyAnswerRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Parse LaTeX expressions
        correct = parse_latex(request.correctAnswer)
        test = parse_latex(request.testAnswer)

        # Simplify both expressions
        simplified_correct = simplify(correct)
        simplified_test = simplify(test)

        # Check for equivalence
        is_correct = simplified_correct.equals(simplified_test)

        return {
            "isCorrect": bool(is_correct),
            "expected": str(simplified_correct),
            "simplifiedTest": str(simplified_test),
        }
    except (SympifyError, ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")
