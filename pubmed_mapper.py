# -*- coding: utf-8 -*-
"""
PubMed Mapper: A Python library that map PubMed XML to Python object
"""
import re
import json
import codecs
import logging
from os import listdir
from os.path import join
from datetime import date
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

import click
from lxml import etree
from rich.progress import track


logger = logging.getLogger('pubmed-mapper')


MONTHS = {
    'Jan': 1, 'Feb': 2, 'Mar': 3,
    'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9,
    'Sept': 9, 'Oct': 10, 'Nov': 11,
    'Dec': 12,
}
SEASONS = {
    'Spring': 4, 'Summer': 7,
    'Fall': 10, 'Autumn': 10, 'Winter': 1
}


class PubmedMapperError(Exception):
    """PubmedMapper Error"""
    pass


def extract_first(data):
    if not (isinstance(data, list) and (len(data) >= 1)):
        return None
    return data[0]


def get_inner_html(element, strip=True):
    texts = []
    if element.text:
        texts.append(element.text)
    for child in element.getchildren():
        texts.append(etree.tostring(child, encoding=str))
    if element.tail:
        texts.append(element.tail)
    text = ''.join(texts)
    if strip:
        text = text.strip()
    return text


class ArticleId(object):
    def __init__(self, id_type, id_value):
        self.id_type = id_type
        self.id_value = id_value

    def __repr__(self):
        return '%s: %s' % (self.id_type, self.id_value)

    def to_dict(self):
        return {
            'id_type': self.id_type,
            'id_value': self.id_value
        }

    @classmethod
    def parse_element(cls, element):
        return cls(
            id_type=element.get('IdType'),
            id_value=element.text
        )


class PubdateDefaults(object):
    """default year, month, day"""
    default_year = 1
    default_month = 1
    default_day = 1


class PubdateParserYearMonthDay(PubdateDefaults):
    """年份、月份、日期都有"""
    def __call__(self, element):
        year_text = extract_first(element.xpath('./Year/text()'))
        month_text = extract_first(element.xpath('./Month/text()'))
        day_text = extract_first(element.xpath('./Day/text()'))
        if not (year_text and month_text and day_text):
            return None
        if month_text.isdigit():
            month = int(month_text)
        else:
            month = MONTHS[month_text.capitalize()]
        return date(
            year=int(year_text),
            month=month,
            day=int(day_text)
        )


class PubdateParserYearMonth(PubdateDefaults):
    """只有年份、月份"""
    def __call__(self, element):
        year_text = extract_first(element.xpath('./Year/text()'))
        month_text = extract_first(element.xpath('./Month/text()'))
        if not (year_text and month_text):
            return None
        if month_text.isdigit():
            month = int(month_text)
        else:
            month = MONTHS[month_text.capitalize()]
        return date(year=int(year_text), month=month, day=self.default_day)


class PubdateParserYearSeason(PubdateDefaults):
    """只有年份、季节"""
    def __call__(self, element):
        year_text = extract_first(element.xpath('./Year/text()'))
        season_text = extract_first(element.xpath('./Season/text()'))
        if not (year_text and season_text):
            return None
        year = int(year_text)
        month = SEASONS[season_text]
        return date(year=year, month=month, day=self.default_day)


class PubdateParserYearOnly(PubdateDefaults):
    """只有年份"""
    def __call__(self, element):
        year_text = extract_first(element.xpath('./Year/text()'))
        if not year_text:
            return None
        return date(
            year=int(year_text),
            month=self.default_month,
            day=self.default_day
        )


class PubdateParserMedlineDateYearOnly(PubdateDefaults):
    """MedlineDate字段只有年份"""
    pattern = re.compile(r'^(?P<year>\d{4}$)')

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        return date(
            year=year,
            month=self.default_month,
            day=self.default_day
        )


class PubdateParserMedlineDateMonthRange(PubdateDefaults):
    """MedlineDate字段同一年月份有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3})-[a-zA-Z]{3}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month = MONTHS[match.groupdict()['month_text'].capitalize()]
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


class PubdateParserMedlineDateMonthRangeCrossDay(PubdateDefaults):
    """MedlineDate字段同一年月份有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3})-[a-zA-Z]{3} (?P<day>\d{1,2})$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month = MONTHS[match.groupdict()['month_text'].capitalize()]
        day = int(match.groupdict()['day'])
        return date(
            year=year,
            month=month,
            day=day
        )

 
class PubdateParserMedlineDateDayRange(PubdateDefaults):
    """MedlineDate字段同一年月份有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3}) (?P<day>\d{1,2})-\d{1,2}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month = MONTHS[match.groupdict()['month_text'].capitalize()]
        day = int(match.groupdict()['day'])
        return date(
            year=year,
            month=month,
            day=day
        )


class PubdateParserMedlineDateMonthRangeCrossYear(PubdateDefaults):
    """MedlineDate字段不同一年月份有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3})-\d{4} [a-zA-Z]{3}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month = MONTHS[match.groupdict()['month_text'].capitalize()]
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


class PubdateParserMedlineDateRangeYear(PubdateDefaults):
    """MedlineDate字段年份区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4})-\d{4}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        return date(
            year=year,
            month=self.default_month,
            day=self.default_day
        )


class PubdateParserMedlineDateMonthDayRange(PubdateDefaults):
    """MedlineDate字段在同一年月份、日期有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3}) (?P<day>\d{1,2})-[a-zA-Z]{3} \d{1,2}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month = MONTHS[match.groupdict()['month_text'].capitalize()]
        day = int(match.groupdict()['day'])
        return date(
            year=year,
            month=month,
            day=day
        )


class PubdateParserMedlineDateYearRangeWithSeason(PubdateDefaults):
    """eg, 1976-1977 Winter"""
    pattern = re.compile(
        r'^(?P<year>\d{4})-\d{4} (?P<season_text>[a-zA-Z]+)$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        season_text = match.groupdict()['season_text'].capitalize()
        month = SEASONS[season_text]
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


class PubdateParserMedlineDateYearSeasonRange(PubdateDefaults):
    """eg, 1977-1978 Fall-Winter"""
    pattern = re.compile(
        r'^(?P<year>\d{4})-\d{4} (?P<season_text>[a-zA-Z]+)-[a-zA-Z]+$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        season_text = match.groupdict()['season_text'].capitalize()
        month = SEASONS[season_text]
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


PUBDATE_PARSERS = [
    PubdateParserYearMonthDay(),
    PubdateParserYearMonth(),
    PubdateParserYearSeason(),
    PubdateParserYearOnly(),
    PubdateParserMedlineDateYearOnly(),
    PubdateParserMedlineDateMonthRange(),
    PubdateParserMedlineDateMonthRangeCrossDay(),
    PubdateParserMedlineDateDayRange(),
    PubdateParserMedlineDateMonthRangeCrossYear(),
    PubdateParserMedlineDateRangeYear(),
    PubdateParserMedlineDateMonthDayRange(),
    PubdateParserMedlineDateYearRangeWithSeason(),
    PubdateParserMedlineDateYearSeasonRange(),
]


class JournalElementParserMixin(object):
    @staticmethod
    def parse_issn(element):
        return extract_first(element.xpath('./ISSN/text()'))

    @staticmethod
    def parse_issn_type(element):
        issn_element = extract_first(element.xpath('./ISSN'))
        if issn_element is None:
            return None
        return issn_element.get('IssnType')

    @staticmethod
    def parse_title(element):
        return element.xpath('./Title/text()')[0]

    @staticmethod
    def parse_abbr(element):
        return element.xpath('./ISOAbbreviation/text()')[0]


class Journal(JournalElementParserMixin):
    def __init__(self, issn, issn_type, title, abbr):
        self.issn = issn
        self.issn_type = issn_type
        self.title = title
        self.abbr = abbr

    def __repr__(self):
        return self.title

    def to_dict(self):
        return {
            'issn': self.issn,
            'issn_type': self.issn_type,
            'title': self.title,
            'abbr': self.abbr,
        }

    @classmethod
    def parse_element(cls, element):
        issn = cls.parse_issn(element)
        issn_type = cls.parse_issn_type(element)
        title = cls.parse_title(element)
        abbr = cls.parse_abbr(element)
        return cls(
            issn=issn, issn_type=issn_type, title=title, abbr=abbr
        )


class Reference(object):
    def __init__(self, citation, ids):
        self.citation = citation
        self.ids = ids

    def __repr__(self):
        return self.citation

    def to_dict(self):
        return {
            'citation': self.citation,
            'ids': [_.to_dict() for _ in self.ids]
        }

    @classmethod
    def parse_element(cls, element):
        """
        parse <Reference></Reference> tag. eg,
        <Reference>
            <Citation>Metabolism. 2009 Jan;58(1):102-8</Citation>
            <ArticleIdList>
                <ArticleId IdType="pubmed">19059537</ArticleId>
            </ArticleIdList>
        </Reference>
        """
        citation = element.xpath('./Citation/text()')[0]
        ids = [
            ArticleId.parse_element(
                article_id_element
            ) for article_id_element in element.xpath(
                './ArticleIdList/ArticleId'
            )
        ]
        return cls(citation=citation, ids=ids)


class AuthorElementParserMixin(object):
    @staticmethod
    def parse_last_name(element):
        return extract_first(element.xpath('./LastName/text()'))

    @staticmethod
    def parse_forename(element):
        return extract_first(element.xpath('./ForeName/text()'))

    @staticmethod
    def parse_initials(element):
        return extract_first(element.xpath('./Initials/text()'))

    @staticmethod
    def parse_affiliation(element):
        return extract_first(element.xpath('./AffiliationInfo/Affiliation/text()'))


class Author(AuthorElementParserMixin):
    def __init__(self, last_name, forename, initials, affiliation):
        """
        Args:
            last_name: 姓
            forename: 名
            initials:
        """
        self.last_name = last_name
        self.forename = forename
        self.initials = initials
        self.affiliation = affiliation

    def __repr__(self):
        return '%s %s %s' % (self.last_name, self.initials, self.forename)

    def to_dict(self):
        return {
            'last_name': self.last_name,
            'forename': self.forename,
            'initials': self.initials,
            'affiliation': self.affiliation
        }

    @classmethod
    def parse_element(cls, element):
        last_name = cls.parse_last_name(element)
        forename = cls.parse_forename(element)
        initials = cls.parse_initials(element)
        affiliation = cls.parse_affiliation(element)
        return cls(
            last_name=last_name,
            forename=forename,
            initials=initials,
            affiliation=affiliation
        )


class ArticleElementParserMixin(object):
    @staticmethod
    def _parse_pmid(element):
        return element.xpath('./MedlineCitation/PMID/text()')[0]

    @staticmethod
    def parse_ids(element):
        return [
            ArticleId.parse_element(
                article_id_element
            ) for article_id_element in element.xpath(
                './PubmedData/ArticleIdList/ArticleId'
            )
        ]

    @staticmethod
    def parse_title(element):
        title_element = extract_first(element.xpath(
            './MedlineCitation/Article/ArticleTitle'
        ))
        return get_inner_html(title_element)

    @staticmethod
    def parse_abstract(element):
        paragraphs = []
        for abstract_text_element in element.xpath(
                './MedlineCitation/Article/Abstract/AbstractText'
        ):
            label = abstract_text_element.get('Label', None)
            sub_title = ''
            if label:
                label = label.capitalize()
                sub_title = '<strong>%s: </strong>' % label
            paragraph = '<p>%s%s</p>' % (sub_title, get_inner_html(abstract_text_element))
            paragraphs.append(paragraph)
        return ''.join(paragraphs)

    @staticmethod
    def parse_keywords(element):
        return element.xpath('./MedlineCitation/KeywordList/Keyword/text()')

    @staticmethod
    def parse_mesh_headings(element):
        return element.xpath(
            './MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName/text()'
        )

    @staticmethod
    def parse_authors(element):
        return [
            Author.parse_element(element) for element in element.xpath(
                './MedlineCitation/Article/AuthorList/Author'
            )
        ]

    @staticmethod
    def parse_journal(element):
        return Journal.parse_element(
            element.xpath('./MedlineCitation/Article/Journal')[0]
        )

    @staticmethod
    def parse_volume(element):
        return extract_first(element.xpath(
            './MedlineCitation/Article/Journal/JournalIssue/Volume/text()'
        ))

    @staticmethod
    def parse_issue(element):
        return extract_first(element.xpath(
            './MedlineCitation/Article/Journal/JournalIssue/Issue/text()'
        ))

    @staticmethod
    def parse_references(element):
        return [
            Reference.parse_element(
                reference_element
            ) for reference_element in element.xpath(
                './PubmedData/ReferenceList/Reference'
            )
        ]

    @staticmethod
    def parse_pubdate(element):
        pubdate_element = element.xpath(
            './MedlineCitation/Article/Journal/JournalIssue/PubDate'
        )[0]
        pubdate = None
        for parser in PUBDATE_PARSERS:
            pubdate = parser(pubdate_element)
            if pubdate:
                break
        if pubdate is None:
            raise PubmedMapperError('日期无法解析，日期格式：%s' % etree.tostring(
                pubdate_element, encoding='utf-8', pretty_print=True
            ))
        return pubdate


class Article(ArticleElementParserMixin):
    def __init__(
            self,
            pmid,
            ids,
            title,
            abstract,
            keywords,
            mesh_headings,
            authors,
            journal,
            volume,
            issue,
            references,
            pubdate
    ):
        self.pmid = pmid
        self.ids = ids
        self.title = title
        self.abstract = abstract
        self.keywords = keywords
        self.mesh_headings = mesh_headings
        self.authors = authors
        self.journal = journal
        self.volume = volume
        self.issue = issue
        self.references = references
        self.pubdate = pubdate

    def __repr__(self):
        return self.title

    def to_dict(self):
        return {
            'pmid': self.pmid,
            'ids': [_.to_dict() for _ in self.ids],
            'title': self.title,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'mesh_headings': self.mesh_headings,
            'authors': [author.to_dict() for author in self.authors],
            'journal': self.journal.to_dict(),
            'volume': self.volume,
            'issue': self.issue,
            'references': [reference.to_dict() for reference in self.references],
            'pubdate': self.pubdate.strftime('%Y-%m-%d')
        }

    @classmethod
    def parse_element(cls, element):
        pmid = cls._parse_pmid(element)
        ids = cls.parse_ids(element)
        title = cls.parse_title(element)
        abstract = cls.parse_abstract(element)
        keywords = cls.parse_keywords(element)
        mesh_headings = cls.parse_mesh_headings(element)
        authors = cls.parse_authors(element)
        journal = cls.parse_journal(element)
        volume = cls.parse_volume(element)
        issue = cls.parse_issue(element)
        references = cls.parse_references(element)
        pubdate = cls.parse_pubdate(element)
        return Article(
            pmid=pmid,
            ids=ids,
            title=title,
            abstract=abstract,
            keywords=keywords,
            mesh_headings=mesh_headings,
            authors=authors,
            journal=journal,
            volume=volume,
            issue=issue,
            references=references,
            pubdate=pubdate
        )

    @classmethod
    def parse_pmid(cls, pmid):
        url = ('https://eutils.ncbi.nlm.nih.gov'
               '/entrez/eutils/efetch.fcgi?'
               'db=pubmed&id=%s&retmode=xml') % pmid
        try:
            handle = urlopen(url)
        except (URLError, HTTPError) as e:
            logger.warning('cannot download %s', pmid)
            logger.exception(e)
            return None
        root = etree.parse(handle)
        element = root.xpath('/PubmedArticleSet/PubmedArticle')[0]
        return cls.parse_element(element)


@click.group()
@click.option(
    '--log-file', type=click.Path(exists=False),
    default='pubmed-mapper.log', show_default=True,
    help='log file'
)
@click.option(
    '--log-level', default='INFO', show_default=True,
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    help='log level'
)
def pubmed_mapper(log_file, log_level):
    """
    A Python library map PubMed XML to Python object
    """
    logging.basicConfig(filename=log_file, level=log_level)


@pubmed_mapper.command(name='pmid')
@click.option(
    '-p', '--pmid', required=True,
    help='PubMed ID, eg, 32329900'
)
def parse_pmid(pmid):
    """
    parse PubMed ID, eg, 32329900
    """
    try:
        article = Article.parse_pmid(pmid)
        print(json.dumps(article.to_dict(), indent=4))
    except Exception as e:
        logger.error('cannot parse %s', pmid)
        logger.exception(e)
    return 0


@pubmed_mapper.command(name='file')
@click.option(
    '-i', '--infile', required=True,
    type=click.Path(exists=True),
    help='input PubMed HTML file'
)
@click.option(
    '-o', '--outfile', required=True,
    type=click.Path(exists=False),
    help='output file, each line is a JSON string for Article object'
)
def parse_file(infile, outfile):
    """
    parse single PubMed XML file
    """
    with codecs.open(infile, encoding='utf-8') as fp:
        root = etree.parse(fp)
    with codecs.open(outfile, 'w', encoding='utf-8') as fp:
        for pubmed_article_element in track(
            root.xpath('/PubmedArticleSet/PubmedArticle'),
            description='Parsing...'
        ):
            try:
                article = Article.parse_element(pubmed_article_element)
                fp.write('%s\n' % json.dumps(article.to_dict()))
            except Exception as e:
                pmid = Article._parse_pmid(pubmed_article_element)
                logger.error('cannot parse %s', pmid)
                logger.exception(e)
    return 0


@pubmed_mapper.command(name='directory')
@click.option(
    '-i', '--indir', required=True,
    type=click.Path(exists=True),
    help='input PubMed XML directory'
)
@click.option(
    '-o', '--outfile', required=True,
    type=click.Path(exists=False),
    help='output file, each line is a JSON string for Article object'
)
def parse_directory(indir, outfile):
    """
    parser a directory who contains multiple PubMed XML files
    """
    with codecs.open(outfile, 'w', encoding='utf-8') as writer:
        for infile in track(listdir(indir), description='Parsing...'):
            infile = join(indir, infile)
            with codecs.open(infile, encoding='utf-8') as reader:
                root = etree.parse(reader)
                for pubmed_article_element in root.xpath('/PubmedArticleSet/PubmedArticle'):
                    try:
                        article = Article.parse_element(pubmed_article_element)
                        writer.write('%s\n' % json.dumps(article.to_dict()))
                    except Exception as e:
                        pmid = Article._parse_pmid(pubmed_article_element)
                        logger.error('cannot parse %s', pmid)
                        logger.exception(e)
    return 0
