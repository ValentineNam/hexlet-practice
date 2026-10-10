"""Запускает тесты единственного ядра вместо копии реализации."""
import importlib.util
import sys
from pathlib import Path

logic_dir = Path(__file__).resolve().parents[1] / 'Реализация ядра бизнес-логики (Расчеты и алгоритмы)'
sys.path.insert(0, str(logic_dir))
spec = importlib.util.spec_from_file_location('core_test_discount', logic_dir / 'test_discount.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TestPartnerDiscount = module.TestPartnerDiscount
