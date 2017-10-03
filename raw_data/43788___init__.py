import re
from openstates.utils import url_xpath

from pupa.scrape import Jurisdiction, Organization
from .people import COLegislatorScraper
from .committees import COCommitteeScraper
from .bills import COBillScraper
from .events import COEventScraper


class Colorado(Jurisdiction):
    division_id = "ocd-division/country:us/state:co"
    classification = "government"
    name = "Colorado"
    url = "http://leg.colorado.gov/"
    scrapers = {
        'people': COLegislatorScraper,
        'committees': COCommitteeScraper,
        'bills': COBillScraper,
        'events': COEventScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "identifier": "2011A",
            "name": "2011 Regular Session",
            "start_date": "2011-01-26"
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "identifier": "2012A",
            "name": "2012 Regular Session",
            "start_date": "2012-01-11"
        },
        {
            "_scraped_name": "2012 First Extraordinary Session",
            "classification": "special",
            "identifier": "2012B",
            "name": "2012 First Extraordinary Session",
            "start_date": "2012-05-14"
        },
        {
            "_scraped_name": "2013 Regular/Special Session",
            "classification": "primary",
            "identifier": "2013A",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2014 Regular/Special Session",
            "classification": "primary",
            "identifier": "2014A",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "classification": "primary",
            "identifier": "2015A",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016 Regular Session",
            "classification": "primary",
            "identifier": "2016A",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "identifier": "2017A",
            "name": "2017 Regular Session",
            "start_date": "2017-01-11",
            "end_date": "2017-05-10",
        }
    ]
    ignored_scraped_sessions = [
        "2013 Legislative Session",
        "2012 First Special Session",
        "2012 Legislative Session",
        "2011 Legislative Session",
        "2010 Legislative Session",
        "2009 Legislative Session",
        "2008 Legislative Session",
        "2007 Legislative Session",
        "2006 First Special Session",
        "2006 Legislative Session",
        "2005 Legislative Session",
        "2004 Legislative Session",
        "2003 Legislative Session",
        "2002 First Special Session",
        "2002 Legislative Session",
        "2001 Second Special Session",
        "2001 First Special Session",
        "2001 Legislative Session",
        "2000 Legislative Session",
        "2010 Regular/Special Session"
    ]

    def get_organizations(self):
        legislature_name = "Colorado General Assembly"
        lower_chamber_name = "House"
        lower_seats = 65
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 35
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)
        executive = Organization('Office of the Governor', classification='executive')

        for n in range(1, upper_seats + 1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats + 1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield executive
        yield upper
        yield lower

    def get_session_list(self):
        tags = url_xpath('http://www.leg.state.co.us/clics/clics2014a/cslFrontPages.nsf/'
                         'PrevSessionInfo?OpenForm', "//font/text()")
        sessions = []
        regex = "2[0-9][0-9][0-9]\ .*\ Session"

        for tag in tags:
            sess = re.findall(regex, tag)
            for session in sess:
                sessions.append(session)

        tags = url_xpath('http://www.leg.state.co.us/CLICS/CLICS2016A/csl.nsf/Home?OpenForm'
                         '&amp;BaseTarget=Bottom', "//font/text()")
        for tag in tags:
            sess = re.findall(regex, tag)
            for session in sess:
                sessions.append(session)

        return sessions
