
from enum import Enum, auto

class Templates(Enum):
    KVIT = "Квитанция растаможки"
    TPO = "ТПО"

class KvitSteps(Enum):
    FULL_NAME = auto()
    ADDRESS = auto()
    PASSPORT_NUMBER = auto()
    PASSPORT_ISSUED_BY = auto()
    PASSPORT_ISSUED_DATE = auto()
    CUSTOMS_RUB = auto()
    DATE = auto()

class TPOSteps(Enum):
    FULL_NAME = auto()
    ADDRESS = auto()
    PASSPORT_NUMBER = auto()
    PASSPORT_ISSUED_BY = auto()
    PASSPORT_ISSUED_DATE = auto()
    CAR_MODEL = auto()
    VIN_CODE = auto()
    CAR_RELEASE_YEAR = auto()
    ENGINE_VOLUME = auto()
    PRICE_RUB = auto()
    CUSTOMS_RUB = auto()
    TPO_DATE = auto()

def get_questions(template: Templates):
    if template == Templates.KVIT:
        return {
            KvitSteps.FULL_NAME: "Введите ФИО плательщика:",
            KvitSteps.ADDRESS: "Адрес плательщика:",
            KvitSteps.PASSPORT_NUMBER: "Серия и номер паспорта:",
            KvitSteps.PASSPORT_ISSUED_BY: "Кем выдан паспорт:",
            KvitSteps.PASSPORT_ISSUED_DATE: "Дата выдачи паспорта (дд.мм.гггг):",
            KvitSteps.CUSTOMS_RUB: "Сумма растаможки в рублях:",
            KvitSteps.DATE: "Дата оформления документа (дд.мм.гггг):",
        }
    elif template == Templates.TPO:
        return {
            TPOSteps.FULL_NAME: "Введите ФИО плательщика:",
            TPOSteps.ADDRESS: "Адрес плательщика:",
            TPOSteps.PASSPORT_NUMBER: "Серия и номер паспорта:",
            TPOSteps.PASSPORT_ISSUED_BY: "Кем выдан паспорт:",
            TPOSteps.PASSPORT_ISSUED_DATE: "Дата выдачи паспорта (дд.мм.гггг):",
            TPOSteps.CAR_MODEL: "Марка/модель автомобиля:",
            TPOSteps.VIN_CODE: "VIN автомобиля:",
            TPOSteps.CAR_RELEASE_YEAR: "Год выпуска автомобиля:",
            TPOSteps.ENGINE_VOLUME: "Объем двигателя (см3):",
            TPOSteps.PRICE_RUB: "Стоимость авто в рублях:",
            TPOSteps.CUSTOMS_RUB: "Сумма растаможки в рублях:",
            TPOSteps.TPO_DATE: "Дата ТПО (дд.мм.гггг):",
        }
