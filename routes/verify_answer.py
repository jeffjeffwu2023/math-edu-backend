from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sympy import simplify, sympify
from sympy.parsing.latex import parse_latex
from sympy.core.sympify import SympifyError
from routes.auth import get_current_user
import re

router = APIRouter(prefix="/api/verify-answer", tags=["verify-answer"])

class AnswerItem(BaseModel):
    value: str = Field(..., description="The answer value (LaTeX or text)")
    type: str = Field(..., description="The type of the answer ('latex' or 'text')")

class VerifyAnswerRequest(BaseModel):
    questionType: str  # For future use
    correctAnswerRelationship: str  # "or" or "and" for multiple correct answers
    correctAnswers: list[AnswerItem]  # Array of answer objects
    testAnswers: list[AnswerItem]  # Array of test answer objects

def parse_answer(value: str, answer_type: str):
    """Parse the answer based on its type, returning a SymPy expression or raw value."""
    try:
        if answer_type == "latex":
            return simplify(parse_latex(value))
        elif answer_type == "text":
            # Attempt to convert text to a SymPy expression if it's a number
            try:
                return simplify(sympify(value))
            except SympifyError:
                return value  # Return raw string if not convertible
        else:
            raise ValueError(f"Unsupported answer type: {answer_type}")
    except (SympifyError, ValueError, TypeError) as e:
        raise ValueError(f"Invalid {answer_type} value '{value}': {str(e)}")

@router.post("/", response_model=dict)
async def verify_answer(request: VerifyAnswerRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Filter out empty answers
        request.correctAnswers = [ans for ans in request.correctAnswers if ans.value.strip()]
        request.testAnswers = [ans for ans in request.testAnswers if ans.value.strip()]
        
        # Ensure correctAnswers and testAnswers are not empty
        if not request.correctAnswers:
            raise HTTPException(status_code=400, detail="At least one correct answer is required")
        if not request.testAnswers:
            raise HTTPException(status_code=400, detail="At least one test answer is required")

        # Parse and simplify all correct answers
        simplified_corrects = []
        for i, ans in enumerate(request.correctAnswers):
            if ans.value.strip():
                try:
                    simplified_corrects.append(parse_answer(ans.value, ans.type))
                except ValueError as e:
                    print(f"Failed to parse correctAnswer[{i}]: '{ans.value}' (type: {ans.type}) - Error: {str(e)}")
                    continue  # Skip invalid entries

        if not simplified_corrects:
            raise HTTPException(status_code=400, detail="No valid correct answers provided")


        # log the simplified correct answers for debugging
        print("Simplified correct answers:", simplified_corrects)   

        # Parse and simplify all test answers
        simplified_tests = []
        for i, ans in enumerate(request.testAnswers):
            if ans.value.strip():
                try:
                    simplified_tests.append(parse_answer(ans.value, ans.type))
                except ValueError as e:
                    print(f"Failed to parse testAnswer[{i}]: '{ans.value}' (type: {ans.type}) - Error: {str(e)}")
                    continue  # Skip invalid entries

        if not simplified_tests:
            raise HTTPException(status_code=400, detail="No valid test answers provided")

        # log the simplified test answers for debugging
        print("Simplified test answers:", simplified_tests) 

        # Evaluate based on correctAnswerRelationship
        results = []
        if request.correctAnswerRelationship == "and":
            if len(simplified_tests) != len(simplified_corrects):
                raise HTTPException(status_code=400, detail="Number of test answers must match number of correct answers for 'and' relationship")
            for i, (simplified_test, simplified_correct) in enumerate(zip(simplified_tests, simplified_corrects)):
                # log the current test and correct answer for debugging
                print(f"Comparing testAnswer[{i}]: '{simplified_test}' with correctAnswer[{i}]: '{simplified_correct}'")
                is_correct = False
                # Handle different types: compare symbolically or as strings if not convertible
                if (isinstance(simplified_test, str) or isinstance(simplified_correct, str)) and not (simplified_test.is_number and simplified_correct.is_number):
                    is_correct = str(simplified_test) == str(simplified_correct)
                    #log the comparison result
                    print(f"String comparison result for testAnswer[{i}]: {is_correct}")
                else:
                    is_correct = simplified_test.equals(simplified_correct)
                    if simplified_test.is_number and simplified_correct.is_number:
                        precision = 10
                        rounded_test = round(float(simplified_test), precision)
                        rounded_correct = round(float(simplified_correct), precision)
                        is_correct = rounded_test == rounded_correct
                # log the is_correct result
                print(f"Is testAnswer[{i}] correct? {is_correct}")
                results.append({
                    "testAnswer": str(simplified_test),
                    "isCorrect": is_correct,
                    "expectedAnswer": str(simplified_correct)
                })
        elif request.correctAnswerRelationship == "or":
            for simplified_test in simplified_tests:
                is_correct = any(
                    (isinstance(simplified_test, str) or isinstance(simplified_correct, str)) and not (simplified_test.is_number and simplified_correct.is_number) and str(simplified_test) == str(simplified_correct)
                    or (not isinstance(simplified_test, str) and not isinstance(simplified_correct, str) and simplified_test.equals(simplified_correct))
                    for simplified_correct in simplified_corrects
                )
                if all(simplified_correct.is_number for simplified_correct in simplified_corrects) and simplified_test.is_number:
                    precision = 10
                    rounded_test = round(float(simplified_test), precision)
                    is_correct = any(
                        round(float(simplified_correct), precision) == rounded_test
                        for simplified_correct in simplified_corrects
                    )
                results.append({
                    "testAnswer": str(simplified_test),
                    "isCorrect": is_correct,
                    "expectedAnswers": [str(simplified_correct) for simplified_correct in simplified_corrects]
                })
        else:
            raise HTTPException(status_code=400, detail="Invalid correctAnswerRelationship: must be 'or' or 'and'")

        # Determine overall isCorrect based on relationship and all test answers
        overall_is_correct = all(result["isCorrect"] for result in results) if request.correctAnswerRelationship == "and" else any(result["isCorrect"] for result in results)

        return {
            "isCorrect": overall_is_correct,
            "correctAnswers": [str(simplified_correct) for simplified_correct in simplified_corrects],
            "results": results
        }
    except (SympifyError, ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")