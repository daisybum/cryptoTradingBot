"""
설정 관리 모듈

이 모듈은 YAML 설정 파일을 로드하고 환경 변수를 통합하는 기능을 제공합니다.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


def load_config(config_path: str) -> Dict[str, Any]:
    """
    YAML 설정 파일을 로드하고 환경 변수와 통합합니다.

    Args:
        config_path (str): 설정 파일 경로

    Returns:
        Dict[str, Any]: 로드된 설정

    Raises:
        FileNotFoundError: 설정 파일을 찾을 수 없는 경우
        yaml.YAMLError: YAML 파싱 오류가 발생한 경우
    """
    # .env 파일 로드 (있는 경우)
    project_root = Path(__file__).parent.parent.parent.absolute()
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    # 설정 파일 로드
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 환경 변수로 설정 보강
    config = _enrich_config_with_env_vars(config)

    return config


def _enrich_config_with_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    환경 변수를 사용하여 설정을 보강합니다.
    환경 변수 이름은 대문자와 밑줄로 변환됩니다.
    예: database.postgresql.password -> DATABASE_POSTGRESQL_PASSWORD

    Args:
        config (Dict[str, Any]): 원본 설정

    Returns:
        Dict[str, Any]: 환경 변수로 보강된 설정
    """
    # 중첩된 설정을 평면화하여 환경 변수 이름 생성
    flat_config = _flatten_dict(config)
    
    # 각 평면화된 키에 대해 환경 변수 확인
    for flat_key, value in flat_config.items():
        env_key = flat_key.upper().replace(".", "_")
        env_value = os.environ.get(env_key)
        
        if env_value is not None:
            # 원래 설정에 환경 변수 값 적용
            _set_nested_value(config, flat_key.split("."), env_value)
    
    return config


def _flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    중첩된 딕셔너리를 평면화합니다.

    Args:
        d (Dict[str, Any]): 평면화할 딕셔너리
        parent_key (str, optional): 부모 키. 기본값은 빈 문자열입니다.
        sep (str, optional): 키 구분자. 기본값은 "."입니다.

    Returns:
        Dict[str, Any]: 평면화된 딕셔너리
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _set_nested_value(d: Dict[str, Any], keys: list, value: Any) -> None:
    """
    중첩된 딕셔너리에 값을 설정합니다.

    Args:
        d (Dict[str, Any]): 대상 딕셔너리
        keys (list): 키 경로
        value (Any): 설정할 값
    """
    if len(keys) == 1:
        d[keys[0]] = _convert_value_type(d.get(keys[0]), value)
        return
    
    if keys[0] not in d:
        d[keys[0]] = {}
    
    _set_nested_value(d[keys[0]], keys[1:], value)


def _convert_value_type(original_value: Any, new_value: str) -> Any:
    """
    원래 값의 타입에 맞게 새 값을 변환합니다.

    Args:
        original_value (Any): 원래 값
        new_value (str): 변환할 문자열 값

    Returns:
        Any: 변환된 값
    """
    if original_value is None:
        return new_value
    
    original_type = type(original_value)
    
    if original_type == bool:
        return new_value.lower() in ("true", "yes", "1", "y")
    elif original_type == int:
        return int(new_value)
    elif original_type == float:
        return float(new_value)
    elif original_type == list:
        return new_value.split(",")
    
    return new_value


# DEAD CODE: def get_config_value(config: Dict[str, Any], key_path: str, default: Optional[Any] = None) -> Any:
    """
    설정에서 중첩된 값을 가져옵니다.

    Args:
        config (Dict[str, Any]): 설정 딕셔너리
        key_path (str): 점으로 구분된 키 경로 (예: "database.postgresql.host")
        default (Any, optional): 키가 없을 경우 반환할 기본값

    Returns:
        Any: 찾은 값 또는 기본값
    """
    keys = key_path.split(".")
    result = config
    
    for key in keys:
        if not isinstance(result, dict) or key not in result:
            return default
        result = result[key]
    
    return result
