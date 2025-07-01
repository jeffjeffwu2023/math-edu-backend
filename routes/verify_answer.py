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
    correctAnswers: list[str]  # Array of LaTeX strings for multiple correct answers
    testAnswer: str  # Single LaTeX string for test answer

@router.post("/", response_model=dict)
async def verify_answer(request: VerifyAnswerRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Ensure correctAnswer is not empty
        if not request.correctAnswers or all(not ans.strip() for ans in request.correctAnswers):
            raise HTTPException(status_code=400, detail="At least one correct answer is required")

        # Parse and simplify all correct answers
        simplified_corrects = []
        for i, ans in enumerate(request.correctAnswers):
            if ans.strip():  # Skip empty strings
                try:
                    correct = parse_latex(ans)
                    simplified_corrects.append(simplify(correct))
                except (SympifyError, ValueError, TypeError) as e:
                    print(f"Failed to parse correctAnswer[{i}]: '{ans}' - Error: {str(e)}")
                    continue  # Skip invalid entries but continue with others

        # Parse and simplify test answer
        try:
            test = parse_latex(request.testAnswer)
            simplified_test = simplify(test)
        except (SympifyError, ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid test answer: {str(e)}")

        # Check for equivalence with any correct answer
        is_correct = False
        if simplified_corrects:
            is_correct = any(
                simplified_correct.equals(simplified_test)
                for simplified_correct in simplified_corrects
            )

            # If they're numbers, round to a reasonable precision (e.g., 10 decimal places) to handle floating-point errors
            if all(simplified_correct.is_number for simplified_correct in simplified_corrects) and simplified_test.is_number:
                precision = 10
                rounded_test = round(float(simplified_test), precision)
                is_correct = any(
                    round(float(simplified_correct), precision) == rounded_test
                    for simplified_correct in simplified_corrects
                )

        return {
            "isCorrect": bool(is_correct),
            "correctAnswers": [str(simplified_correct) for simplified_correct in simplified_corrects],
            "simplifiedTest": str(simplified_test),
        }
    except (SympifyError, ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")