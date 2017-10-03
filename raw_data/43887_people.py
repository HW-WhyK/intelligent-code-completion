import re

import lxml.html
import scrapelib
from pupa.scrape import Person, Scraper


abbr = {'D': 'Democratic', 'R': 'Republican'}


class MIPersonScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        if chamber == 'upper':
            yield from self.scrape_upper(chamber)
        elif chamber == 'lower':
            yield from self.scrape_lower(chamber)
        else:
            yield from self.scrape_upper(chamber)
            yield from self.scrape_lower(chamber)

    def scrape_lower(self, chamber):
        url = 'http://www.house.mi.gov/mhrpublic/frmRepList.aspx'
        table = [
            "website",
            "district",
            "name",
            "party",
            "location",
            "phone",
            "email"
        ]

        data = self.get(url).text
        doc = lxml.html.fromstring(data)

        # skip two rows at top
        for row in doc.xpath('//table[@id="grvRepInfo"]/*'):
            tds = row.xpath('.//td')
            if len(tds) == 0:
                continue
            metainf = {}
            for i in range(0, len(table)):
                metainf[table[i]] = tds[i]
            district = str(int(metainf['district'].text_content().strip()))
            party = metainf['party'].text_content().strip()
            phone = metainf['phone'].text_content().strip()
            email = metainf['email'].text_content().strip()
            leg_url = metainf['website'].xpath("./a")[0].attrib['href']
            name = metainf['name'].text_content().strip()
            if name == 'Vacant' or re.match(r'^District \d{1,3}$', name):
                self.warning('District {} appears vacant, and will be skipped'.format(district))
                continue

            office = metainf['location'].text_content().strip()
            office = re.sub(
                ' HOB',
                ' Anderson House Office Building\n124 North Capitol Avenue\nLansing, MI 48933',
                office
            )
            office = re.sub(
                ' CB',
                ' State Capitol Building\nLansing, MI 48909',
                office
            )

            try:
                photo_url = self.get_photo_url(leg_url)[0]
            except (scrapelib.HTTPError, IndexError):
                photo_url = ''
                self.warning('no photo url for %s', name)

            person = Person(name=name, district=district, party=abbr[party],
                            primary_org='lower', image=photo_url)

            person.add_link(leg_url)
            person.add_source(leg_url)

            person.add_contact_detail(type='address', value=office, note='Capitol Office')
            person.add_contact_detail(type='voice', value=phone, note='Capitol Office')
            person.add_contact_detail(type='email', value=email, note='Capitol Office')

            yield person

    def scrape_upper(self, chamber):
        url = 'http://www.senate.michigan.gov/senatorinfo_list.html'
        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        for row in doc.xpath('//table[not(@class="calendar")]//tr')[3:]:
            if len(row) != 7:
                continue

            # party, dist, member, office_phone, office_fax, office_loc
            party, dist, member, contact, phone, fax, loc = row.getchildren()
            if (party.text_content().strip() == "" or
                    'Lieutenant Governor' in member.text_content()):
                continue

            party = abbr[party.text]
            district = dist.text_content().strip()
            name = member.text_content().strip()
            name = re.sub(r'\s+', " ", name)

            if name == 'Vacant':
                self.info('district %s is vacant', district)
                continue

            leg_url = member.xpath('a/@href')[0]
            office_phone = phone.text
            office_fax = fax.text

            office_loc = loc.text
            office_loc = re.sub(
                ' Farnum Bldg',
                ' Farnum Office Building\n125 West Allegan Street\nLansing, MI 48933',
                office_loc
            )
            office_loc = re.sub(
                ' Capitol Bldg',
                ' State Capitol Building\nLansing, MI 48909',
                office_loc
            )

            # email addresses aren't on the list page anymore but they
            # are on the page linked off "Contact Me"

            # data has a typo in a row
            contact_url = [
                a for a in row.xpath(".//a")
                if a.text in ('Contact Me', 'Conact Me')][0].get('href')
            contact_html = self.get(contact_url).text
            contact_doc = lxml.html.fromstring(contact_html)

            email = None
            header_email = contact_doc.xpath("//a[@class='header_email']")
            if header_email:
                email = header_email[0].text
            else:
                # not using the most common template, but maybe they
                # dropped their email on the page somewhere
                links = contact_doc.xpath('//a') or []
                text_email = [a for a in links
                              if 'mailto:' in (a.get('href') or '')]
                if text_email:
                    email = text_email[0].text

            person = Person(name=name, district=district, party=party, primary_org='upper')

            person.add_link(leg_url)
            person.add_source(leg_url)

            person.add_contact_detail(type='address', value=office_loc, note='Capitol Office')
            person.add_contact_detail(type='voice', value=office_phone, note='Capitol Office')
            person.add_contact_detail(type='fax', value=office_fax, note='Capitol Office')
            if email:
                person.add_contact_detail(type='email', value=email, note='Capitol Office')

            yield person

    def get_photo_url(self, url):
        # broken URL, special cased
        if 'winnie-brinks' in url:
            url = 'https://housedems.com/brinks'

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(url)
        return (
            doc.xpath('//div[contains(@class, "headshotTop")]//img/@src') +  # housedems.com
            doc.xpath('//div[contains(@class, "widget_sp_image")]//img/@src')  # gophouse.org
        )
