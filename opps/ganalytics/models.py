# -*- coding: utf-8 -*-
from urlparse import urlparse

from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.contrib.redirects.models import Redirect

from googleanalytics.account import filter_operators
from appconf import AppConf

from opps.core.models import Publishable, Date
from opps.containers.models import Container


FIELDS_FILTER = ['pageviews', 'pagePath']


class GAnalyticsConf(AppConf):
    ACCOUNT = u''
    PASSWORD = u''
    APIKEY = u''
    STATUS = True
    RUN_EVERY_HOUR = u"*/4"
    RUN_EVERY_MINUTE = u"*"
    RUN_EVERY_DAY_OF_WEEK = u"*"
    RANGE_DAYS = 30

    class Meta:
        prefix = 'opps_ganalytics'


class Filter(Date):
    field = models.CharField(_(u"Field"), max_length=50,
                             choices=zip(FIELDS_FILTER, FIELDS_FILTER))
    operator = models.CharField(_(u"Operator"), choices=zip(filter_operators,
                                                            filter_operators),
                                max_length=3)
    expression = models.CharField(_(u"Expression"), max_length=255,
                                  help_text=_(u'Regular expression'))
    combined = models.CharField(_(u"Combined"), max_length=3, null=True,
                                blank=True, choices=(('OR', 'OR'),
                                                     ('AND', 'AND')))

    def __unicode__(self):
        tmpl = "{self.field} {self.operator} {self.expression} {self.combined}"
        return tmpl.format(self=self)

    class Meta:
        verbose_name = _(u'Filter')
        verbose_name_plural = _(u'Filters')


class QueryFilter(models.Model):
    query = models.ForeignKey('ganalytics.Query',
                              verbose_name=_(u'Query'),
                              null=True, blank=True,
                              related_name='queryfilter_queries',
                              on_delete=models.SET_NULL)
    filter = models.ForeignKey('ganalytics.Filter',
                               verbose_name=_('Filter'),
                               null=True, blank=True,
                               related_name='queryfilter_filters',
                               on_delete=models.SET_NULL)
    order = models.PositiveIntegerField(_(u'Order'), default=0)

    def __unicode__(self):
        return self.query.name

    class Meta:
        verbose_name = _(u'Query Filter')
        verbose_name_plural = _(u'Query Filters')


class Query(Publishable):
    name = models.CharField(_(u"Name"), max_length=140)
    account = models.ForeignKey('ganalytics.Account')
    start_date = models.DateTimeField(_(u"Start date"), null=True, blank=True)
    end_date = models.DateTimeField(_(u"End date"), null=True, blank=True)
    metrics = models.CharField(_(u"Metrics"), choices=(
        ('pageviews', 'Pageviews'),
        ('uniquepageviews', 'Unique Pageviews')), max_length=15)
    filter = models.ManyToManyField('ganalytics.Filter', null=True,
                                    blank=True, related_name='query_filters',
                                    through='ganalytics.QueryFilter')

    def __unicode__(self):
        return u"{0}-{1}".format(self.account.title, self.name)

    class Meta:
        verbose_name = _(u'Query')
        verbose_name_plural = _(u'Queries')


class Report(Date):
    url = models.CharField(_('URL'), max_length=255, unique=True,
                           db_index=True)

    # Get Google Analytics
    pageview = models.IntegerField(default=0, db_index=True)
    timeonpage = models.CharField(
        _(u'Time on page'),
        max_length=25,
        default=0
    )
    entrances = models.IntegerField(default=0)

    # Opps join
    container = models.ForeignKey(
        'containers.Container',
        null=True,
        blank=True,
        related_name='report_containers',
        on_delete=models.SET_NULL
    )

    __unicode__ = lambda self: "{} -> {}".format(self.url, self.container)

    def save(self, *args, **kwargs):

        self.container = None

        self.url = self.url.strip()

        if not self.url.startswith("http"):
            self.url = "http://{}".format(self.url)

        try:
            redirects = Redirect.objects.filter(
                old_path=self.url,
            )

            # try without scheme://domain
            if not redirects:
                _url = urlparse(self.url)
                redirects = Redirect.objects.filter(
                    old_path=_url.path
                )

            if redirects:
                redirect = redirects[0]
                _site = redirect.site
                _slug = redirect.new_path.split('/')[-1]
                if _slug.endswith('.html'):
                    _slug = _slug.replace('.html', '')

                containers = Container.objects.filter(
                    slug=_slug,
                    site=_site,
                )

                for container in containers:
                    if container.channel.long_slug in redirect.new_path:
                        self.container = container
                        break

        except:
            pass

        try:
            if not self.container:
                url = urlparse(self.url)

                slug = url.path.split('/')[-1]
                if slug.endswith('.html'):
                    slug = slug.replace('.html', '')

                """
                long_slug = '/'.join(url.path.split('/')[:-1]).partition('/')[-1]
                # The long slug above does not works because of links liks
                # /album, /video, /link etc..
                """
                domain = url.netloc

                containers = Container.objects.filter(
                    slug=slug,
                    site_domain=domain,
                    # channel_long_slug=long_slug
                )
                #print "#### model url:", url, slug
                #print "### model containers:", containers
                for container in containers:
                    if container.channel.long_slug in url.path:
                        self.container = container
                        # print "found:", container
                        break
        except:
            # print str(e)
            pass

        super(Report, self).save(*args, **kwargs)


    class Meta:
        verbose_name = _(u'Report')
        verbose_name_plural = _(u'Reports')


class Account(Date):
    account_id = models.IntegerField()
    account_name = models.CharField(
        _(u"Account name"),
        max_length=150
    )
    title = models.CharField(_(u'Title'), max_length=255)
    profile_id = models.IntegerField(unique=True)

    def __unicode__(self):
        return u"{0}-{1}".format(self.title, self.profile_id)

    class Meta:
        verbose_name = _(u'Account')
        verbose_name_plural = _(u'Accounts')
