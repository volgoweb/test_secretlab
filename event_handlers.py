# -*- coding: utf-8 -*-
import datetime
from collections import OrderedDict
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _


class EventHandlerFabric:
    """
    Класс создает объект обработчика события
    согласно типу события.
    """
    ETYPE_1 = 1
    ETYPE_2 = 2
    ETYPE_3 = 3
    ETYPE_4 = 4
    ETYPE_5 = 5
    ETYPE_6 = 6
    ETYPES = OrderedDict([
        (ETYPE_1, 'Event type 1'),
        (ETYPE_2, 'Event type 2'),
        (ETYPE_3, 'Event type 3'),
        (ETYPE_4, 'Event type 4'),
        (ETYPE_5, 'Event type 5'),
        (ETYPE_6, 'Event type 6'),
    ])

    @staticmethod
    def create_handler(cls, etype, member):
        if etype not in Event.ETYPES.keys():
            raise ValueError
        if not isinstance(member, Member):
            raise TypeError

        event = self.save_event(etype, member)
        if etype == cls.ETYPE_1:
            return HandlerSimple(event=event, experience_increase=1)
        elif etype == cls.ETYPE_2:
            return HandlerByFirstNumberRepeats(event=event, experience_increase=3, count_repeats=2)
        elif etype == cls.ETYPE_3:
            return HandlerSimple(event=event, experience_increase=5)
        elif etype == cls.ETYPE_4:
            return HandlerInPeriod(
                event=event,
                experience_increase=1,
                count_repeats_in_period=2,
                period_type=HandlerInPeriodMixin.PT_DAY
            )
        elif etype == cls.ETYPE_5:
            return HandlerSimpleByLevel(
                event=event,
                exp_increase_by_level={
                    1: 3,
                    2: 3,
                    3: 4,
                    4: 4,
                    5: 12,
                }
            )
        elif etype == cls.ETYPE_6:
            return HandleByLevelWithLimit(
                event=event,
                exp_increase_by_level={
                    1: 3,
                    2: 3,
                    3: 4,
                    4: 4,
                    5: 12,
                },
                limit_by_level={
                    1: 5,
                    2: 5,
                    3: 5,
                    4: 5,
                    5: 5,
                }
                
            )

    @staticmethod
    def save_event(cls, etype, member):
        """
        Сохраняет данные о событии в базе данных.
        """
        event = Event.create(
            etype=etype,
            member=member,
        )
        if not event.pk:
            raise Exception(_('Event saving error.'))
        return event


class EventHandlerBase(object):
    """
    Базовый класс обработчика события.
    """
    def __init__(self, event, *args, **kwargs):
        if not isinstance(event, Event):
            raise TypeError

    def handle(self):
        raise NotImplementedError

    @property
    def count_same_events(self):
        if not hasattr(self, '_count_same_events'):
            self._count_same_events = Event.objects.all().of_type(self.event.etype).count()
        return self._count_same_events


class HandlerSimple(EventHandlerBase):
    """
    Класс обработчика событий, для которых опыт участника
    увеличивается на указанную величину независимо
    ни от прошлых событий ни от текущего уровня участника.
    """
    def __init__(self, event, experience_increase):
        super(HandlerSimple, self).__init__(event, experience_increase)
        self.event = event
        if experience_increase <= 0:
            raise ValueError
        if type(experience_increase) not in (int, long):
            raise TypeError
        self.experience_increase = experience_increase

    def handle(self):
        self.event.member.experience += self.experience_increase
        self.event.member.save()


class HandlerByFirstNumberRepeats(HandlerSimple):
    """
    Обработывает события, которые ограничены количеством
    (то есть опыт дается только за N раз,
    например, участник может совершить действие 100 раз,
    но получит опыт только за первые 2 и не больше). 
    """
    def __init__(self, event, experience_increase, count_repeats, *args, **kwargs):
        super(HandlerByFirstNumberRepeats, self).__init__(event, *args, **kwargs)
        if count_repeats <= 0 or experience_increase <= 0:
            raise ValueError
        if type(experience_increase) not in (int, long):
            raise TypeError
        self.experience_increase = experience_increase
        self.count_repeats = count_repeats

    def handle(self):
        if self.count_same_events <= count_repeats:
            self.event.member.experience += self.experience_increase
            self.event.save()


class HandlerInPeriodMixin:
    """
    Класс, добавляющий обработчику события функционал,
    необходимый при зависимости от совершенных ранее событий.
    """
    PT_DAY = 1
    # Можно добавить типы периода "неделя", "месяц"
    PERIOD_TYPES = OrderedDict([
        (PT_DAY, _('Day')),
    ])

    EXCEPTION_MESSAGES = {
        'invalid_period_type': _('Argument "peiod_type" can be equal one of values: "%(types)s"') % {'types': PERIOD_TYPES.keys()},
    }

    def __init__(self, *args, **kwargs):
        if 'period_type' not in kwargs:
            # TODO можно написать кастомный Exception
            raise ValueError(_('Function "__init__" did not take keyword argument "period_type".'))
        if period_type not in self.PERIOD_TYPES.keys():
            raise ValueError(EXCEPTION_MESSAGES['invalid_period_type'])
        self.period_type = period_type

    def get_period_bounds(self):
        """
        Возвращает границы указанного периода.
        """
        return HandlerInPeriodMixin._get_period_bounds(self.period_type)

    @staticmethod
    def _get_period_bounds(cls, period_type):
        """
        Возвращает границы указанного периода.
        """
        # TODO в дальнейшем можно сделать фабрику периодов,
        # которая будет возвращать объект, наследующий единый интерфейс.
        # Объект периода будет иметь метод получения границ периода.
        if period_type == self.PT_DAY:
            now = datetime.datetime.now()
            dt_to = now
            dt_from = now.replace(hour=0, minute=0, second=0)
            return (dt_from, dt_to)
        else:
            raise ValueError(EXCEPTION_MESSAGES['invalid_period_type'])


    @staticmethod
    def get_bounds_of_all_period_types(cls):
        """
        Возвращает границы всех используемых в системе периодов.
        """
        bounds = []
        for pt in cls.PERIOD_TYPES.keys():
            bounds.append(cls._get_period_bounds(pt))
        return bounds

    def count_same_events_in_period(self, event, period_bounds):
        if len(period_bounds) != 2 \
                or not isinstance(period_bounds[0], datetime) \
                or not isinstance(period_bounds[1], datetime):
            raise ValueError(_('Argument "period_bounds" could be list with two datetime objects.'))      
        member_events_statistics_type = ContentType.objects.get(app_label='test', model='MemberEventsStatistics')
        MemberEventsStatistics = member_events_statistics_type.model_class()
        return MemberEventsStatistics.objects.count_for_member(
            member=event.member,
            etype=event.etype,
            period_bounds=period_bounds,
        )



class HandlerInPeriod(HandlerInPeriodMixin, HandlerSimple):
    """
    Обработчик событий, которые ограничены количеством раз
    в определенный промежуток времени
    (например, 3 раза в день, то есть, совершив события 10 раз
    в рамках одного дня, участник получит опыт только за первые 3 раза)
    """
    def __init__(self, event, experience_increase, count_repeats_in_period, period_type):
        super(HandlerInPeriod, self).__init__(event, experience_increase, count_repeats_in_period, period_type)
        if count_repeats_in_period <= 0:
            raise ValueError(_('Argument "count_repeats_in_period" could be a positive integer value.'))
        if experience_increase <= 0:
            raise ValueError(_('Argument "experience_increase" could be a positive integer value.'))
        if type(experience_increase) not in (int, long):
            raise TypeError(_('Type of argument "experience_increase" could be a integer or long.'))
        self.experience_increase = experience_increase
        self.count_repeats_in_period = count_repeats_in_period

    def handle(self):
        period_bounds = self.get_period_bounds()
        count_in_period = self.count_same_events_in_period(
            event=self.event,
            period_bounds=period_bounds
        )
        if count_in_period < self.count_repeats_in_period:
            self.event.member.experience += self.experience_increase
            self.event.member.save()


class HandlerByLevel(EventHandlerBase):
    def __init__(self, exp_increase_by_level, *args, **kwargs):
        if not isinstance(exp_increase_by_level, dict):
            raise TypeError
        self.exp_increase_by_level = exp_increase_by_level


class HandlerSimpleByLevel(HandlerByLevel):
    def __init__(self, exp_increase_by_level):
        super(HandlerSimpleByLevel, self).__init__(exp_increase_by_level, *args, **kwargs)

    def handle(self):
        member_level = self.event.member.level
        increase = self.exp_increase_by_level.get(member_level, 0)
        if increase:
            self.event.member.experience += increase
            self.event.member.save()


class HandleByLevelWithLimit(HandlerByLevel):
    def __init__(self, event, exp_increase_by_level, limit_by_level):
        super(HandleByLevelWithLimit, self).__init__(exp_increase_by_level, limit_by_level)
        if not isinstance(limit_by_level, dict):
            raise TypeError
        self.limit_by_level = limit_by_level

    def handle(self):
        limit = self.limit_by_level.get(self.event.member.level)
        member_events_statistics_type = ContentType.objects.get(app_label='test', model='MemberEventsStatistics')
        MemberEventsStatistics = member_events_statistics_type.model_class()
        count_events = MemberEventsStatistics.objects.count_for_member(
            member=self.event.member,
            etype=self.event.etype,
            for_current_level=True,
        )
        if count_events <= limit:
            self.event.member.experience += exp_increase_by_level.get(self.event.member.level, 0)
            self.event.member.save()


def register_event(etype, member):
    """
    Регистрация события.
    При наступлении какого-то события просто вызываем эту функцию,
    а она уже сохранит данные о событии в БД,
    исходя из параметров события изменит опыт участника,
    который инициализировал это событие.
    """
    h = EventHandlerFabric.create_handler(etype=event_type, member=member)
    h.handle()
