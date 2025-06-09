#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
파라미터 구성 관련 API 라우터
"""

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api_server.models.database import get_db
from src.api_server.models.models import Parameter, ParameterResponse, ParameterCreate, ParameterUpdate
from src.api_server.auth.auth import get_current_active_user
from src.strategy_engine.strategy_loader import StrategyLoader

router = APIRouter(
    prefix="/parameters",
    tags=["parameters"],
    dependencies=[Depends(get_current_active_user)],
    responses={401: {"description": "Unauthorized"}},
)

@router.get("/", response_model=List[ParameterResponse])
async def get_parameters(
    strategy: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    파라미터 목록 조회
    
    - **strategy**: 전략 필터
    """
    query = db.query(Parameter)
    
    if strategy:
        query = query.filter(Parameter.strategy == strategy)
    
    parameters = query.all()
    
    return parameters

@router.get("/{parameter_id}", response_model=ParameterResponse)
async def get_parameter(parameter_id: int, db: Session = Depends(get_db)):
    """
    특정 파라미터 조회
    
    - **parameter_id**: 조회할 파라미터 ID
    """
    parameter = db.query(Parameter).filter(Parameter.id == parameter_id).first()
    
    if not parameter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parameter with ID {parameter_id} not found"
        )
    
    return parameter

@router.post("/", response_model=ParameterResponse)
async def create_parameter(
    parameter: ParameterCreate,
    db: Session = Depends(get_db)
):
    """
    새 파라미터 생성
    """
    # 중복 확인
    existing = db.query(Parameter).filter(
        Parameter.name == parameter.name,
        Parameter.strategy == parameter.strategy
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameter '{parameter.name}' already exists for strategy '{parameter.strategy}'"
        )
    
    db_parameter = Parameter(**parameter.dict())
    
    db.add(db_parameter)
    db.commit()
    db.refresh(db_parameter)
    
    return db_parameter

@router.put("/{parameter_id}", response_model=ParameterResponse)
async def update_parameter(
    parameter_id: int,
    parameter_update: ParameterUpdate,
    db: Session = Depends(get_db)
):
    """
    파라미터 업데이트
    
    - **parameter_id**: 업데이트할 파라미터 ID
    """
    db_parameter = db.query(Parameter).filter(Parameter.id == parameter_id).first()
    
    if not db_parameter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parameter with ID {parameter_id} not found"
        )
    
    # 업데이트할 필드만 업데이트
    for key, value in parameter_update.dict(exclude_unset=True).items():
        setattr(db_parameter, key, value)
    
    db.commit()
    db.refresh(db_parameter)
    
    return db_parameter

@router.delete("/{parameter_id}")
async def delete_parameter(parameter_id: int, db: Session = Depends(get_db)):
    """
    파라미터 삭제
    
    - **parameter_id**: 삭제할 파라미터 ID
    """
    db_parameter = db.query(Parameter).filter(Parameter.id == parameter_id).first()
    
    if not db_parameter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parameter with ID {parameter_id} not found"
        )
    
    db.delete(db_parameter)
    db.commit()
    
    return {"status": "success", "message": f"Parameter with ID {parameter_id} deleted"}

@router.get("/strategy/{strategy_name}", response_model=Dict[str, str])
async def get_strategy_parameters(
    strategy_name: str,
    db: Session = Depends(get_db)
):
    """
    특정 전략의 현재 파라미터 조회
    
    - **strategy_name**: 전략 이름
    """
    try:
        # 전략 로더를 통해 전략 클래스 로드
        strategy_loader = StrategyLoader()
        strategy_class = strategy_loader.load_strategy(strategy_name)
        
        # 전략 인스턴스 생성
        strategy_instance = strategy_class({})
        
        # 기본 파라미터 가져오기
        if hasattr(strategy_instance, 'default_params'):
            default_params = strategy_instance.default_params
        else:
            # 기본 파라미터가 없는 경우, 클래스 속성 중 파라미터로 사용될 수 있는 것들 수집
            default_params = {}
            for attr_name in dir(strategy_instance):
                if not attr_name.startswith('_') and not callable(getattr(strategy_instance, attr_name)):
                    attr_value = getattr(strategy_instance, attr_name)
                    if isinstance(attr_value, (int, float, str, bool)):
                        default_params[attr_name] = str(attr_value)
        
        # 데이터베이스에서 저장된 파라미터 가져오기
        db_params = db.query(Parameter).filter(Parameter.strategy == strategy_name).all()
        
        # 저장된 파라미터로 기본 파라미터 업데이트
        for param in db_params:
            default_params[param.name] = param.value
        
        return default_params
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy parameters: {str(e)}"
        )

@router.put("/strategy/{strategy_name}")
async def update_strategy_parameters(
    strategy_name: str,
    parameters: Dict[str, str],
    db: Session = Depends(get_db)
):
    """
    특정 전략의 파라미터 업데이트
    
    - **strategy_name**: 전략 이름
    - **parameters**: 업데이트할 파라미터 (키-값 쌍)
    """
    try:
        # 전략 로더를 통해 전략 클래스 로드 (유효성 검사)
        strategy_loader = StrategyLoader()
        strategy_loader.load_strategy(strategy_name)
        
        # 각 파라미터 업데이트 또는 생성
        for name, value in parameters.items():
            # 기존 파라미터 찾기
            db_param = db.query(Parameter).filter(
                Parameter.name == name,
                Parameter.strategy == strategy_name
            ).first()
            
            if db_param:
                # 기존 파라미터 업데이트
                db_param.value = value
            else:
                # 새 파라미터 생성
                db_param = Parameter(
                    name=name,
                    value=value,
                    strategy=strategy_name,
                    description=f"Parameter for {strategy_name}"
                )
                db.add(db_param)
        
        db.commit()
        
        return {"status": "success", "message": f"Parameters for strategy '{strategy_name}' updated"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy parameters: {str(e)}"
        )
