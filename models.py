# -*- coding: utf-8 -*-
from django.db import models
from django.core.validators import MaxValueValidator
from django.contrib.auth.models import AbstractUser
from django.utils.translation import ugettext as _
from django.dispatch import receiver
from django.db.models.signals import post_save

from event_handlers import EventHandlerFabric, HandlerInPeriodMixin

# TODO добавить учет таймзоны для участников и для событий


class Member(AbstractUser):
    """
    Модель участника.
    Как я понимаю в системе эта модель должна быть
    основной модель, описывающей пользователя.
    Поэтому ее наследуем от встроенного в django
    класса пользователя и в settings изменим 
    параметр активной модели пользователя.
    """
    MAX_LEVEL = 5
    LEVEL_VALIDATORS = [MaxValueValidator(MAX_LEVEL)]
    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'
        abstract = False
        verbose_name = _('Member')
        verbose_name_plural = _('Members')

    experience = models.PositiveIntegerField(_('Experience'), default=0, blank=True)
    level = models.PositiveSmallIntegerField(_('Level'), validators=LEVEL_VALIDATORS, default=0, blank=True)


class EventQueryset(models.query.QuerySet):
    def of_type(self, etype):
        return self.filter(etype=etype)

    def in_period(self, dt_from, dt_to):
        return self.filter(
            datetime__lte=dt_to,
            datetime__gte=from_to,
        )


class EventManager(models.Manager):
    def get_queryset(self):
        return EventQueryset(self.model).all()
        

class Event(models.Model):
    """
    Модель события.
    """
    etype = models.PositiveSmallIntegerField(choices=EventHandlerFabric.ETYPES.items(), db_index=True)
    member = models.ForeignKey('Member', verbose_name=_('Member'), db_index=True)
    datetime = models.DateTimeField(_('Date and time'), auto_now_add=True)

    objects = EventManager()

    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Events')


class MemberEventsStatisticsManager(models.Manager):
    def increase_count(self, member, etype, period_bounds=None):
        qs = self.get_queryset()
        qs = qs.filter(
            member=member,
            current_member_level=member.level,
            etype=etype,
        )
        if period_bounds:
            qs = qs.filter(
                period_from=period_bounds[0],
                period_to=period_bounds[1],
            )
        if qs.exists():
            qs.update(count=F('count') + 1)
        else:
            MemberEventsStatistics.create(
                member=member,
                current_member_level=member.level,
                etype=etype,
                period_from=period_bounds[0],
                period_to=period_bounds[1],
                count=1,
            )

    def count_for_member(self, member, etype, period_bounds=None, for_current_level=None):
        conditions = {
            'member': member,
            'etype': etype,
        }
        if period_bounds:
            conditions.update({
                'period_from': period_bounds[0],
                'period_to': period_bounds[1],
            })
        if for_current_level:
            conditions.update({
                'current_member_level': member.level,
            })
        result = qs.filter(**conditions).aggregate(summary_count=Sum('count'))
        return result['summary_count']



class MemberEventsStatistics(models.Model):
    """
    Вспомогательная модель, хранящая
    статистику по разным типам событий
    за разные периоды для каждого участника.
    Она служит для ускорения определения
    условий начисления опыта участников.
    """
    member = models.ForeignKey('Member', verbose_name=_('Member'), db_index=True)
    current_member_level = models.PositiveSmallIntegerField(_('Current level'), validators=Member.LEVEL_VALIDATORS, default=0, blank=True)
    etype = models.PositiveSmallIntegerField(choices=EventHandlerFabric.ETYPES.items(), db_index=True)
    period_from = models.DateTimeField(null=True, blank=True)
    period_from = models.DateTimeField(null=True, blank=True)
    count = models.PositiveSmallIntegerField()

    objects = MemberEventsStatisticsManager()

@receiver(post_save, sender=Event)
def post_save_event(instance, **kwargs):
    for bounds in HandlerInPeriodMixin.get_bounds_of_all_period_types():
        # увеличиваем статистику по количеству событий
        # такого типа за определенный период
        # (по каждому используемому типу периода)
        # у данного участника
        MemberEventsStatistics.objects.increase_count(
            member=instance.member,
            etype=instance.etype,
            period_bounds=bounds,
        )
    # увеличиваем статистику по общему количеству событий
    # такого типа у данного участника
    MemberEventsStatistics.objects.increase_count(
        member=instance.member,
        etype=instance.etype,
    )


# signal смены уровня в зависимости от опыта

# В любом месте проекта,
# где определяется какое событие было совершено вставляем:
# register_event(etype, member)
