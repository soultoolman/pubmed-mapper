# -*- coding: utf-8 -*-
from datetime import date

import pytest
from lxml import etree

import pubmed_mapper


@pytest.fixture
def author_element():
    xml = """
    <Author ValidYN="Y">
        <LastName>Garganeeva</LastName>
        <ForeName>A A</ForeName>
        <Initials>AA</Initials>
        <AffiliationInfo>
            <Affiliation>Cardiology Research Institute, Tomsk NRMC, 111-А, Kievskaya str., Tomsk 634012, Russian Federation; kitti-lit@yandex.ru.</Affiliation>
        </AffiliationInfo>
    </Author>
    """
    return etree.fromstring(xml)


def test_extract_first():
    assert pubmed_mapper.extract_first(None) is None
    assert pubmed_mapper.extract_first([]) is None
    assert pubmed_mapper.extract_first([0]) == 0


def test_article_id():
    xml = '<ArticleId IdType="pii">cc12514</ArticleId>'
    element = etree.fromstring(xml)
    article_id = pubmed_mapper.ArticleId.parse_element(element)
    assert article_id.id_type == 'pii'
    assert article_id.id_value == 'cc12514'


def test_pubdate_parser_year_month_day():
    data1 = """
    <PubDate>
        <Year>2014</Year>
        <Month>6</Month>
        <Day>15</Day>
    </PubDate>
    """
    data2 = """
    <PubDate>
        <Year>2014</Year>
        <Month>Jun</Month>
        <Day>15</Day>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserYearMonthDay()
    element1 = etree.fromstring(data1)
    element2 = etree.fromstring(data2)
    pubdate1 = parser(element1)
    pubdate2 = parser(element2)
    assert pubdate1 == date(2014, 6, 15)
    assert pubdate2 == date(2014, 6, 15)


def test_pubdate_parser_year_month():
    data = """
    <PubDate>
        <Year>2014</Year>
        <Month>Jun</Month>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserYearMonth()
    element = etree.fromstring(data)
    pubdate = parser(element)
    assert pubdate == date(2014, 6, 1)


def test_pubdate_parser_year_season():
    data = """
    <PubDate>
        <Year>2014</Year>
        <Season>Autumn</Season>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserYearSeason()
    element = etree.fromstring(data)
    pubdate = parser(element)
    assert pubdate == date(2014, 10, 1)


def test_pubdate_parser_year_only():
    data = """
    <PubDate>
        <Year>2014</Year>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserYearOnly()
    element = etree.fromstring(data)
    pubdate = parser(element)
    assert pubdate == date(2014, 1, 1)


def test_pubdate_parser_medline_date_year_only():
    data = """
    <PubDate>
        <MedlineDate>2014</MedlineDate>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserMedlineDateYearOnly()
    element = etree.fromstring(data)
    pubdate = parser(element)
    assert pubdate == date(2014, 1, 1)


def test_pubdate_parser_medline_date_year_month_range():
    data = """
    <PubDate>
        <MedlineDate>2014 Jun-Nov</MedlineDate>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserMedlineDateMonthRange()
    element = etree.fromstring(data)
    pubdate = parser(element)
    assert pubdate == date(2014, 6, 1)


def test_pubdate_parser_medline_date_year_day_range():
    data = """
    <PubDate>
        <MedlineDate>2014 Jun 15-17</MedlineDate>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserMedlineDateDayRange()
    element = etree.fromstring(data)
    pubdate = parser(element)
    assert pubdate == date(2014, 6, 15)


def test_pubdate_parser_medline_date_month_range_cross_year():
    xml = """
    <PubDate>
        <MedlineDate>1975 Dec-1976 Jan</MedlineDate>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserMedlineDateMonthRangeCrossYear()
    element = etree.fromstring(xml)
    pubdate = parser(element)
    assert pubdate == date(1975, 12, 1)


def test_pubdate_parser_medline_date_range_year():
    xml = """
    <PubDate>
        <MedlineDate>1975-1976</MedlineDate>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserMedlineDateRangeYear()
    element = etree.fromstring(xml)
    pubdate = parser(element)
    assert pubdate == date(1975, 1, 1)


def test_pubdate_parser_medline_date_month_day_range():
    xml = """
    <PubDate>
        <MedlineDate>1976 Aug 28-Sep 4</MedlineDate>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserMedlineDateMonthDayRange()
    element = etree.fromstring(xml)
    pubdate = parser(element)
    assert pubdate == date(1976, 8, 28)


def test_pubdate_parser_medline_date_year_range_with_season():
    xml = """
    <PubDate>
        <MedlineDate>1976-1977 Winter</MedlineDate>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserMedlineDateYearRangeWithSeason()
    element = etree.fromstring(xml)
    pubdate = parser(element)
    assert pubdate == date(1976, 1, 1)


def test_pubdate_parser_medline_date_year_season_range():
    xml = """
    <PubDate>
        <MedlineDate>1977-1978 Fall-Winter</MedlineDate>
    </PubDate>
    """
    parser = pubmed_mapper.PubdateParserMedlineDateYearSeasonRange()
    element = etree.fromstring(xml)
    pubdate = parser(element)
    assert pubdate == date(1977, 10, 1)


def test_affiliation_parser_city_postcode_city():
    text = "Department of Pharmacy, University of Bonn, 53113 Bonn, Germany."
    aff = pubmed_mapper.AffiliationParserCityPostcodeCity()(text)
    assert aff is not None
    assert aff.college == 'Department of Pharmacy'
    assert aff.university == 'University of Bonn'
    assert aff.address is None
    assert aff.city == 'Bonn'
    assert aff.city_postcode == '53113'
    assert aff.province is None
    assert aff.country == 'Germany'


def test_affiliation_parser_city_city_postcode():
    text = "College of Bioinformatics Science and Technology, Harbin Medical University, Harbin 150081, China."
    aff = pubmed_mapper.AffiliationParserCityCityPostcode()(text)
    assert aff is not None
    assert aff.college == 'College of Bioinformatics Science and Technology'
    assert aff.university == 'Harbin Medical University'
    assert aff.address is None
    assert aff.city == 'Harbin'
    assert aff.city_postcode == '150081'
    assert aff.province is None
    assert aff.country == 'China'


def test_affiliation_parser_city_comma_city_postcode():
    text = "Department of Animal and Veterinary Sciences, Clemson University, Clemson, SC 29634, USA."
    aff = pubmed_mapper.AffiliationParserCityCommaCityPostcode()(text)
    assert aff is not None
    assert aff.college == 'Department of Animal and Veterinary Sciences'
    assert aff.university == 'Clemson University'
    assert aff.address is None
    assert aff.city == 'Clemson'
    assert aff.city_postcode == 'SC 29634'
    assert aff.province is None
    assert aff.country == 'USA'


def test_affiliation_parser_city_province():
    text = "Pharmaceutical Research Department, Allen and Hanburys Research Ltd., Ware, Herts, U.K."
    aff = pubmed_mapper.AffiliationParserCityProvince()(text)
    assert aff is not None
    assert aff.college == 'Pharmaceutical Research Department'
    assert aff.university == 'Allen and Hanburys Research Ltd.'
    assert aff.address is None
    assert aff.city == 'Ware'
    assert aff.city_postcode is None
    assert aff.province == 'Herts'
    assert aff.country == 'U.K'


def test_affiliation_parser_street_number_comma_street():
    text = ("Cardiology Research Institute, Tomsk NRMC, 111-А, Kievskaya str., "
            "Tomsk 634012, Russian Federation; kitti-lit@yandex.ru.")
    aff = pubmed_mapper.AffiliationParserStreetNumberCommaStreet()(text)
    assert aff is not None
    assert aff.college == 'Cardiology Research Institute'
    assert aff.university == 'Tomsk NRMC'
    assert aff.address == '111-А, Kievskaya str.'
    assert aff.city == 'Tomsk'
    assert aff.city_postcode == '634012'
    assert aff.province is None
    assert aff.country == 'Russian Federation'


def test_affiliation_parser_street():
    text = ("Institute of Health Sciences, Collegium Medicum, "
            "University of Zielona Gora, Zyty 28 St., 65-046 Zielona Góra, Poland.")
    aff = pubmed_mapper.AffiliationParserStreet()(text)
    assert aff is not None
    assert aff.college == 'Collegium Medicum'
    assert aff.university == 'University of Zielona Gora'
    assert aff.address == 'Zyty 28 St.'
    assert aff.city == 'Zielona Góra'
    assert aff.city_postcode == '65-046'
    assert aff.province is None
    assert aff.country == 'Poland'


class TestAuthorElementParserMixin(object):
    def test_parse_last_name(self, author_element):
        last_name = pubmed_mapper.AuthorElementParserMixin.parse_last_name(author_element)
        assert last_name == 'Garganeeva'

    def test_parse_forename(self, author_element):
        forename = pubmed_mapper.AuthorElementParserMixin.parse_forename(author_element)
        assert forename == 'A A'

    def test_parse_initials(self, author_element):
        initials = pubmed_mapper.AuthorElementParserMixin.parse_initials(author_element)
        assert initials == 'AA'


class TestReference(object):
    def test_parse_element(self):
        xml = """
        <Reference>
            <Citation>Metabolism. 2009 Jan;58(1):102-8</Citation>
            <ArticleIdList>
                <ArticleId IdType="pubmed">19059537</ArticleId>
            </ArticleIdList>
        </Reference>
        """
        element = etree.fromstring(xml)
        reference = pubmed_mapper.Reference.parse_element(element)
        assert reference.citation == 'Metabolism. 2009 Jan;58(1):102-8'
        assert len(reference.ids) == 1
        assert reference.ids[0].id_type == 'pubmed'
        assert reference.ids[0].id_value == '19059537'


class TestArticleElementParserMixin(object):
    def test_parse_pmid(self):
        xml = """
        <PubmedArticle>
            <MedlineCitation Status="MEDLINE" Owner="NLM">
                <PMID Version="1">29325141</PMID>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        pmid = pubmed_mapper.ArticleElementParserMixin.parse_pmid(element)
        assert pmid == '29325141'

    def test_parse_ids(self):
        xml = """
        <PubmedArticle>
            <PubmedData>
                <ArticleIdList>
                    <ArticleId IdType="pubmed">29325141</ArticleId>
                    <ArticleId IdType="pii">4793372</ArticleId>
                    <ArticleId IdType="doi">10.1093/nar/gkx1311</ArticleId>
                    <ArticleId IdType="pmc">PMC5815097</ArticleId>
                </ArticleIdList>
            </PubmedData>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        ids = pubmed_mapper.ArticleElementParserMixin.parse_ids(element)
        assert len(ids) == 4
        assert ids[0].id_type == 'pubmed'
        assert ids[0].id_value == '29325141'
        assert ids[1].id_type == 'pii'
        assert ids[1].id_value == '4793372'
        assert ids[2].id_type == 'doi'
        assert ids[2].id_value == '10.1093/nar/gkx1311'
        assert ids[3].id_type == 'pmc'
        assert ids[3].id_value == 'PMC5815097'

    def test_parse_title(self):
        xml = """
        <PubmedArticle>
            <MedlineCitation Status="MEDLINE" Owner="NLM">
                <Article PubModel="Print">
                    <ArticleTitle>LncMAP: Pan-cancer atlas of long noncoding RNA-mediated transcriptional network perturbations.</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        title = pubmed_mapper.ArticleElementParserMixin.parse_title(element)
        assert title == 'LncMAP: Pan-cancer atlas of long noncoding RNA-mediated transcriptional network perturbations.'

    def test_parse_abstract(self):
        xml = """
        <PubmedArticle>
            <MedlineCitation Status="MEDLINE" Owner="NLM">
                <Article PubModel="Print">
                    <ArticleTitle>LncMAP: Pan-cancer atlas of long noncoding RNA-mediated transcriptional network perturbations.</ArticleTitle>
                    <Abstract>
                        <AbstractText>The paper presents</AbstractText>
                    </Abstract>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        abstract = pubmed_mapper.ArticleElementParserMixin.parse_abstract(element)
        assert abstract == '<p>The paper presents</p>'

    def test_parse_keywords(self):
        xml = """
        <PubmedArticle>
            <MedlineCitation Status="MEDLINE" Owner="NLM">
                <KeywordList Owner="NOTNLM">
                    <Keyword MajorTopicYN="N">acute myocardial infarction</Keyword>
                    <Keyword MajorTopicYN="N">elderly patients</Keyword>
                    <Keyword MajorTopicYN="N">longterm survival</Keyword>
                    <Keyword MajorTopicYN="N">myocardial infarction with ST-segment elevation (STEMI)</Keyword>
                </KeywordList>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        keywords = pubmed_mapper.ArticleElementParserMixin.parse_keywords(element)
        assert keywords == [
            'acute myocardial infarction',
            'elderly patients',
            'longterm survival',
            'myocardial infarction with ST-segment elevation (STEMI)'
        ]

    def test_parse_mesh_headings(self):
        xml = """
        <PubmedArticle>
            <MedlineCitation Status="MEDLINE" Owner="NLM">
                <MeshHeadingList>
                    <MeshHeading>
                        <DescriptorName UI="D000208" MajorTopicYN="N">Acute Disease</DescriptorName>
                    </MeshHeading>
                    <MeshHeading>
                        <DescriptorName UI="D000367" MajorTopicYN="N">Age Factors</DescriptorName>
                    </MeshHeading>
                </MeshHeadingList>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        mesh_heading = pubmed_mapper.ArticleElementParserMixin.parse_mesh_headings(element)
        assert mesh_heading == [
            'Acute Disease',
            'Age Factors'
        ]

    def test_parse_authors(self):
        xml = """
        <PubmedArticle>
            <MedlineCitation Status="MEDLINE" Owner="NLM">
                <Article>
                    <AuthorList CompleteYN="Y">
                        <Author ValidYN="Y">
                            <LastName>Garganeeva</LastName>
                            <ForeName>A A</ForeName>
                            <Initials>AA</Initials>
                            <AffiliationInfo>
                                <Affiliation>Cardiology Research Institute, Tomsk NRMC, 111-А, Kievskaya str., Tomsk 634012, Russian Federation; kitti-lit@yandex.ru.</Affiliation>
                            </AffiliationInfo>
                        </Author>
                        <Author ValidYN="Y">
                            <LastName>Tukish</LastName>
                            <ForeName>O V</ForeName>
                            <Initials>OV</Initials>
                            <AffiliationInfo>
                                <Affiliation>Cardiology Research Institute, Tomsk NRMC, 111-А, Kievskaya str., Tomsk 634012, Russian Federation; kitti-lit@yandex.ru.</Affiliation>
                            </AffiliationInfo>
                        </Author>
                    </AuthorList>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        authors = pubmed_mapper.ArticleElementParserMixin.parse_authors(element)
        assert len(authors) == 2
        assert authors[0].last_name == 'Garganeeva'
        assert authors[0].forename == 'A A'
        assert authors[0].initials == 'AA'
        assert authors[0].affiliation.college == 'Cardiology Research Institute'
        assert authors[0].affiliation.university == 'Tomsk NRMC'
        assert authors[0].affiliation.address == '111-А, Kievskaya str.'
        assert authors[0].affiliation.city == 'Tomsk'
        assert authors[0].affiliation.city_postcode == '634012'
        assert authors[0].affiliation.province is None
        assert authors[0].affiliation.country == 'Russian Federation'
        assert authors[1].last_name == 'Tukish'
        assert authors[1].forename == 'O V'
        assert authors[1].initials == 'OV'
        assert authors[1].affiliation.college == 'Cardiology Research Institute'
        assert authors[1].affiliation.university == 'Tomsk NRMC'
        assert authors[1].affiliation.address == '111-А, Kievskaya str.'
        assert authors[1].affiliation.city == 'Tomsk'
        assert authors[1].affiliation.city_postcode == '634012'
        assert authors[1].affiliation.province is None
        assert authors[1].affiliation.country == 'Russian Federation'

    def test_parse_journal(self):
        xml = """
        <PubmedArticle>
            <MedlineCitation Status="MEDLINE" Owner="NLM">
                <Article PubModel="Print">
                    <Journal>
                        <ISSN IssnType="Electronic">1362-4962</ISSN>
                        <JournalIssue CitedMedium="Internet">
                            <Volume>46</Volume>
                            <Issue>3</Issue>
                            <PubDate>
                                <Year>2018</Year>
                                <Month>02</Month>
                                <Day>16</Day>
                            </PubDate>
                        </JournalIssue>
                        <Title>Nucleic acids research</Title>
                        <ISOAbbreviation>Nucleic Acids Res</ISOAbbreviation>
                    </Journal>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        journal = pubmed_mapper.ArticleElementParserMixin.parse_journal(element)
        assert journal.issn_type == 'Electronic'
        assert journal.issn == '1362-4962'
        assert journal.title == 'Nucleic acids research'
        assert journal.abbr == 'Nucleic Acids Res'

    def test_parse_volume(self):
        data = """
        <PubmedArticle>
            <MedlineCitation>
                <Article>
                    <Journal>
                        <ISSN IssnType="Print">1561-9125</ISSN>
                        <JournalIssue CitedMedium="Print">
                            <Volume>30</Volume>
                            <Issue>5</Issue>
                            <PubDate>
                                <MedlineDate>2017</MedlineDate>
                            </PubDate>
                        </JournalIssue>
                        <Title>Advances in gerontology = Uspekhi gerontologii</Title>
                        <ISOAbbreviation>Adv Gerontol</ISOAbbreviation>
                    </Journal>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(data)
        volume = pubmed_mapper.Article.parse_volume(element)
        assert volume == '30'

    def test_parse_issue(self):
        data = """
        <PubmedArticle>
            <MedlineCitation>
                <Article>
                    <Journal>
                        <ISSN IssnType="Print">1561-9125</ISSN>
                        <JournalIssue CitedMedium="Print">
                            <Volume>30</Volume>
                            <Issue>5</Issue>
                            <PubDate>
                                <MedlineDate>2017</MedlineDate>
                            </PubDate>
                        </JournalIssue>
                        <Title>Advances in gerontology = Uspekhi gerontologii</Title>
                        <ISOAbbreviation>Adv Gerontol</ISOAbbreviation>
                    </Journal>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(data)
        issue = pubmed_mapper.Article.parse_issue(element)
        assert issue == '5'

    def test_parse_references(self):
        xml = """
        <PubmedArticle>
            <PubmedData>
                <ReferenceList>
                    <Reference>
                        <Citation>Metabolism. 2009 Jan;58(1):102-8</Citation>
                        <ArticleIdList>
                            <ArticleId IdType="pubmed">19059537</ArticleId>
                        </ArticleIdList>
                    </Reference>
                    <Reference>
                        <Citation>Clin Nutr. 2012 Dec;31(6):1002-7</Citation>
                        <ArticleIdList>
                            <ArticleId IdType="pubmed">22682085</ArticleId>
                        </ArticleIdList>
                    </Reference>
                </ReferenceList>
            </PubmedData>
        </PubmedArticle>
        """
        element = etree.fromstring(xml)
        references = pubmed_mapper.ArticleElementParserMixin.parse_references(element)
        assert len(references) == 2
        assert references[0].citation == 'Metabolism. 2009 Jan;58(1):102-8'
        assert len(references[0].ids) == 1
        assert references[0].ids[0].id_type == 'pubmed'
        assert references[0].ids[0].id_value == '19059537'
        assert references[1].citation == 'Clin Nutr. 2012 Dec;31(6):1002-7'
        assert len(references[1].ids) == 1
        assert references[1].ids[0].id_type == 'pubmed'
        assert references[1].ids[0].id_value == '22682085'

    def test_parse_pubdate(self):
        data = """
        <PubmedArticle>
            <MedlineCitation>
                <Article>
                    <Journal>
                        <ISSN IssnType="Print">1561-9125</ISSN>
                        <JournalIssue CitedMedium="Print">
                            <Volume>30</Volume>
                            <Issue>5</Issue>
                            <PubDate>
                                <MedlineDate>2017</MedlineDate>
                            </PubDate>
                        </JournalIssue>
                        <Title>Advances in gerontology = Uspekhi gerontologii</Title>
                        <ISOAbbreviation>Adv Gerontol</ISOAbbreviation>
                    </Journal>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """
        element = etree.fromstring(data)
        pubdate = pubmed_mapper.Article.parse_pubdate(element)
        assert pubdate == date(2017, 1, 1)

