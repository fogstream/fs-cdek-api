# -*- coding: future_fstrings -*-
import abc
from abc import abstractmethod
import datetime
from decimal import Decimal
from typing import Any
from typing import Dict
from typing import List
from typing import Optional, Union
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

Date = Union[datetime.datetime, datetime.date]

# compatible with Python 2 *and* 3:
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


class AbstractElement(ABC):
    @abstractmethod
    def to_xml(self):
        raise NotImplementedError


class PreAlert(AbstractElement):
    pre_alert_element = None
    orders = []

    def __init__(self, planned_meeting_date, pvz_code):
        """
        Инициализация создания сводного реестра
        :param planned_meeting_date: Дата планируемой передачи.
        :param pvz_code: Офис-получатель
        """
        self.pre_alert_element = Element(
            'PreAlert',
            PlannedMeetingDate=planned_meeting_date.isoformat(),
            PvzCode=pvz_code,
        )

    def add_order(self, dispatch_number,
                  number = None):
        """
        Добавление заказа к преалерту
        :param str dispatch_number: Номер заказа в системе СДЭК
        :param str number: Номер заказа в системе ИМ
        :return: Элемент заказа
        :rtype: SubElement
        """
        order_element = SubElement(
            self.pre_alert_element,
            'Order',
            DispatchNumber=dispatch_number,
            Number=number,
        )
        self.orders.append(order_element)

        return order_element

    def to_xml(self):
        return self.pre_alert_element


class CallCourier(AbstractElement):
    call_courier_element = None
    calls = []

    def __init__(self, call_count = 1):
        """
        Инициализация вызова курьера для забора груза
        :param int call_count: Количество заявок для вызова курьера в документе
        """
        self.call_courier_element = ElementTree.Element(
            'CallCourier',
            CallCount=call_count,
        )

    def add_call(self, date, time_begin,
                 time_end,
                 dispatch_number = None,
                 sender_city_id = None,
                 sender_phone = None,
                 sender_name = None,
                 weight = None,
                 comment = None,
                 lunch_begin = None,
                 lunch_end = None,
                 ignore_time = False):
        """
        Добавление вызова курьера
        :param date: дата ожидания курьера
        :param time_begin: время начала ожидания
        :param time_end: время окончания ожидания
        :param int dispatch_number: Номер привязанного заказа
        :param int sender_city_id: ID города отправителя по базе СДЭК
        :param str sender_phone: телефон оправителя
        :param str sender_name: ФИО оправителя
        :param int weight: общий вес в граммах
        :param str comment: комментарий
        :param lunch_begin: время начала обеда
        :param lunch_end: время окончания обеда
        :param bool ignore_time: Не выполнять проверки времени приезда курьера
        :return: Объект вызова
        """

        call_element = ElementTree.SubElement(
            self.call_courier_element,
            'Call',
            Date=date.isoformat(),
            TimeBeg=time_begin.isoformat(),
            TimeEnd=time_end.isoformat(),
        )

        call_element.attrib['DispatchNumber'] = dispatch_number
        call_element.attrib['SendCityCode'] = sender_city_id
        call_element.attrib['SendPhone'] = sender_phone
        call_element.attrib['SenderName'] = sender_name
        call_element.attrib['Weight'] = weight
        call_element.attrib['Comment'] = comment
        call_element.attrib['IgnoreTime'] = ignore_time

        if lunch_begin:
            call_element.attrib['LunchBeg'] = lunch_begin.isoformat()
        if lunch_end:
            call_element.attrib['LunchEnd'] = lunch_end.isoformat()

        self.calls.append(call_element)

        return call_element

    @staticmethod
    def add_address(call_element, address_street,
                    address_house, address_flat):
        """Добавление адреса забора посылки.

        :param call_element: Объект вызова курьера
        :param address_street: Улица отправителя
        :param address_house: Дом, корпус, строение отправителя
        :param address_flat: Квартира/Офис отправителя
        :return: Объект адреса вызова
        """
        address_element = ElementTree.SubElement(
            call_element,
            'Address',
            Street=address_street,
            House=address_house,
            Flat=address_flat,
        )

        return address_element

    def to_xml(self):
        return self.call_courier_element


class DeliveryRequest(AbstractElement):
    delivery_request_element = None
    orders = []

    def __init__(self, number, order_count = 1):
        """Инициализация запроса на доставку.

        :param number: Номер заказа
        :param order_count: Количество заказов в документе
        """
        self.number = number
        self.delivery_request_element = ElementTree.Element(
            'DeliveryRequest',
            Number=number,
            OrderCount=order_count,
        )

    def add_order(self, number, tariff_type_code,
                  recipient_name, phone,
                  send_city_code = None,
                  send_city_post_code = None,
                  rec_city_code = None,
                  rec_city_post_code = None,
                  shipping_price = None,
                  comment = None,
                  seller_name = None):
        """Добавление запроса на доставку.

        :param str number: Номер отправления клиента (уникален в пределах
            заказов одного клиента). Идентификатор заказа в ИС Клиента.
        :param int send_city_code: Код города отправителя из базы СДЭК
        :param str send_city_post_code: Почтовый индекс города отправителя
        :param int rec_city_code: Код города получателя из базы СДЭК
        :param str rec_city_post_code: Почтовый индекс города получателя
        :param str recipient_name: Получатель (ФИО)
        :param int tariff_type_code: Код типа тарифа
        :param shipping_price: Доп. сбор ИМ за доставку
        :param str phone: Телефон получателя
        :param str comment: Комментарий особые отметки по заказу
        :param str seller_name: Истинный продавец. Используется при печати
            заказов для отображения настоящего продавца товара,
            торгового названия.
        :return: Объект заказа
        """
        order_element = ElementTree.SubElement(
            self.delivery_request_element,
            'Order',
        )

        order_element.attrib['Number'] = number
        order_element.attrib['SendCityCode'] = send_city_code
        order_element.attrib['SendCityPostCode'] = send_city_post_code
        order_element.attrib['RecCityCode'] = rec_city_code
        order_element.attrib['RecCityPostCode'] = rec_city_post_code
        order_element.attrib['RecipientName'] = recipient_name
        order_element.attrib['TariffTypeCode'] = tariff_type_code
        order_element.attrib['DeliveryRecipientCost'] = shipping_price
        order_element.attrib['Phone'] = phone
        order_element.attrib['Comment'] = comment
        order_element.attrib['SellerName'] = seller_name

        self.orders.append(order_element)
        return order_element

    @staticmethod
    def add_address(
            order_element,
            street = None,
            house = None,
            flat = None,
            pvz_code = None
    ):
        """Добавление адреса доставки.

        :param order_element: Объект заказа
        :param str street: Улица получателя
        :param str house: Дом, корпус, строение получателя
        :param str flat: Квартира/Офис получателя
        :param str pvz_code: Код ПВЗ. Атрибут необходим только
            для заказов с режимом доставки «до склада»
        :return: Объект адреса
        """
        address_element = ElementTree.SubElement(order_element, 'Address')

        if pvz_code:
            address_element.attrib['PvzCode'] = pvz_code
        else:
            address_element.attrib['Street'] = street
            address_element.attrib['House'] = house
            address_element.attrib['Flat'] = flat

        return address_element

    @staticmethod
    def add_package(
            order_element,
            size_a = None,
            size_b = None,
            size_c = None,
            number = None,
            barcode = None,
            weight = None
    ):
        """Добавление посылки.

        Габариты упаковки заполняются только если указаны все три значения.

        :param order_element: Объект заказа
        :param int size_a: Габариты упаковки. Длина (в сантиметрах)
        :param int size_b: Габариты упаковки. Ширина (в сантиметрах)
        :param int size_c: Габариты упаковки. Высота (в сантиметрах)
        :param number: Номер упаковки (можно использовать порядковый номер
            упаковки заказа или номер заказа), уникален в пределах заказа.
            Идентификатор заказа в ИС Клиента.

        :param barcode: Штрих-код упаковки, идентификатор грузоместа.
            Параметр используется для оперирования грузом на складах СДЭК),
            уникален в пределах заказа. Идентификатор грузоместа в ИС Клиента.
        :param int weight: Общий вес (в граммах)
        """

        order_number = order_element.attrib['Number']
        package_number = number or order_number
        barcode = barcode or order_number

        if not (size_a and size_b and size_c):
            size_a = size_b = size_c = None

        package_element = ElementTree.SubElement(
            order_element,
            'Package',
            Number=package_number,
            BarCode=barcode,
            SizeA=size_a,
            SizeB=size_b,
            SizeC=size_c,
            Weight=weight
        )

        return package_element

    @staticmethod
    def add_item(
            package_element,
            weight,
            ware_key,
            cost,
            payment = 0,
            amount = 1,
            comment = ''
    ):
        """Добавление товара в посылку.

        :param package_element: Объект посылки
        :param weight: Вес (за единицу товара, в граммах)
        :param ware_key: Идентификатор/артикул товара/вложения
        :param cost: Объявленная стоимость товара
        :param payment: Оплата за товар при получении
        :param amount: Количество единиц одноименного товара (в штуках).
        :param comment: Наименование товара
            (может также содержать описание товара: размер, цвет)
        """
        item_element = ElementTree.SubElement(
            package_element,
            'Item',
            Amount=amount,
        )
        item_element.attrib['Weight'] = weight
        item_element.attrib['WareKey'] = ware_key
        item_element.attrib['Cost'] = cost
        item_element.attrib['Payment'] = payment
        item_element.attrib['Comment'] = comment

        return item_element

    @staticmethod
    def add_service(order_element,
                    code, count = None):
        """Добавление дополнительной услуги к заказу.

        :param order_element: Объект заказа
        :param code: Тип дополнительной услуги
        :param count: Количество упаковок
        """

        add_service_element = ElementTree.SubElement(
            order_element,
            'AddService',
            ServiceCode=code,
            Count=count,
        )

        return add_service_element

    def to_xml(self):
        return self.delivery_request_element


class CostRequestError(Exception):

    DELIVERY_UNAVAILABLE_CODE = 3

    def __init__(self, error_list):
        # type: (List[Dict[str: Any]]) -> None
        super(CostRequestError, self).__init__(error_list)
        self.error_list = error_list

    def is_delivery_unavailable(self):
        # type: () -> bool
        for error_dict in self.error_list:
            if error_dict['code'] == self.DELIVERY_UNAVAILABLE_CODE:
                return True
        return False


class ShippingService(object):

    HEAVY_ID = 5
    OVER_SIZED_ID = 6

    def __init__(self, service_dict):
        # type: (Dict[str: Any]) -> None
        self.id = service_dict['id']
        self.title = service_dict['title']
        self.price = service_dict.get('price')
        self.rate = service_dict.get('rate')

    def is_heavy(self):
        # type: () -> bool
        return self.id == self.HEAVY_ID

    def is_over_sized(self):
        # type: () -> bool
        return self.id == self.OVER_SIZED_ID

    def __unicode__(self):
        return u'%s - %s' % (self.title, self.price)


class ShippingCost(object):

    @staticmethod
    def parse_date(string):
        # type: (str) -> datetime.date
        return datetime.datetime.strptime(string, "%Y-%m-%d").date()

    def __init__(self, response_dict):
        # type: (Dict[str: Any]) -> None
        if 'error' in response_dict:
            raise CostRequestError(response_dict['error'])
        result = response_dict['result']
        self.price = Decimal(result['price'])
        self.tariff_id = result['tariffId']
        self.delivery_date_min = self.parse_date(result['deliveryDateMin'])
        self.delivery_date_max = self.parse_date(result['deliveryDateMax'])
        self.services = [
            ShippingService(service)
            for service in result.get('services', [])
        ]

    def is_heavy(self):
        # type: () -> bool
        return any(
            service.is_heavy()
            for service in self.services
        )

    def is_over_sized(self):
        # type: () -> bool
        return any(
            service.is_over_sized()
            for service in self.services
        )

    def __unicode__(self):
        return u'%s (%s - %s)' % (self.price, self.delivery_date_min, self.delivery_date_max)
