from unittest.mock import patch

import pandas as pd

from tt_news_scraper.fetching_utils.articles import (
    fetch_express_article_content,
    fetch_guardian_article_content,
)


def test_fetch_express_article_content_works():
    MOCK_INPUT = pd.DataFrame(
        [
            {
                "url": "https://trinidadexpress.com/business/local/fatima-wins-ttsec-investing-debate-competition/article_ce841f96-2c19-4fc6-a539-4e3637d9d646.html",
            },
        ]
    )

    # outputs
    ARTICLE_1_CONTENT = """Fatima College has been crowned champion of the Trinidad and Tobago Securities and Exchange Commission's (TTSEC) inaugural National Investing Debate Competition, following weeks of debate among 22 secondary schools from across the country. The school secured the top award at today's grand final, held at the Government Campus Plaza in Port of Spain, where it faced St Joseph's Convent, San Fernando. Presentation College, Chaguanas, finished third. The competition, which began on September 28, was held under the theme "Our Virtual Assets" and challenged students to examine financial literacy, investor protection and the opportunities and risks associated with virtual assets. Addressing students at the final, TTSEC chief executive officer Kester Guy cautioned that emerging financial technologies, while creating new opportunities, also carried risks that required careful consideration. "New technologies can create opportunities, but an exciting idea still requires careful examination. Prices can change sharply. Fraud can occur. Money can be lost," Guy said. The competition was designed to give students an opportunity to engage with financial concepts while developing skills in research, public speaking, analytical thinking and informed decision-making. Minister of Public Administration and Artificial Intelligence Dominic Smith and Chief Education Officer Peter Smith also delivered remarks at the event. The TTSEC thanked the Ministry of Education for its approval and support, as well as the participating schools, teachers, coaches, judges, parents, sponsors and other partners who contributed to the initiative. The commission said the competition formed part of its wider effort to advance investor education, promote financial literacy and equip young people to make responsible financial decisions."""

    EXPECTED_OUTPUT = pd.DataFrame(
        [
            {
                "url": "https://trinidadexpress.com/business/local/fatima-wins-ttsec-investing-debate-competition/article_ce841f96-2c19-4fc6-a539-4e3637d9d646.html",
                "content": ARTICLE_1_CONTENT,
            }
        ]
    )

    # Mock HTML response for Express article - structure matches real TT Express layout
    MOCK_HTML = f"""<!DOCTYPE html>
<html>
<head><title>Fatima Wins TTSEC Investing Debate</title></head>
<body>
<div class="tnt-article-content">
{ARTICLE_1_CONTENT}
</div>
</body>
</html>"""

    with patch("tt_news_scraper.fetching_utils.articles.requests.get") as mock_get:
        mock_response = type(
            "Response",
            (object,),
            {"ok": True, "text": MOCK_HTML},
        )()
        mock_get.return_value = mock_response

        # call fn
        OBSERVED_OUTPUT = fetch_express_article_content(MOCK_INPUT["url"])

        # check for match
        pd.testing.assert_frame_equal(EXPECTED_OUTPUT, OBSERVED_OUTPUT)


def test_fetch_guardian_article_content_works():
    MOCK_INPUT = pd.DataFrame(
        [
            {
                "url": "https://www.guardian.co.tt/news/four-held-for-drunk-driving-in-tobago-6.2.2698647.671a12a8be",
            },
        ]
    )

    # outputs
    ARTICLE_1_CONTENT = """Four people were arrested for driving under the influence of alcohol during police operations in Tobago on Friday as the Trinidad and Tobago Police Service (TTPS) intensified security for Carnival 2026. The arrests were made during Operation Resolute Shield in Scarborough and Bacolet between 8.30 am and 12.30 pm.According to the TTPS, the four men, aged 30, 28, 40 and 41, were found to have alcohol readings above the legal limit. The highest reading was recorded by a 41-year-old man from Ontario, Canada, at 74 microgrammes of alcohol per 100 millilitres of breath, 39 microgrammes above the permitted limit. The other readings were 68 microgrammes, 59 microgrammes and 43 microgrammes. Police also completed nine stop-and-search forms and issued 13 fixed penalty notices for traffic violations, including failure to wear seat belts, expired inspection stickers, defective tyres, driving without a tint exemption and carrying passengers in a dangerous manner. The exercise focused on the Stink and Dutty event at the Parade Grounds in Bacolet, as well as passengers and vehicles arriving at the Scarborough Port. The TTPS said no traffic-related incidents or major crimes were reported during the operation. In a separate roadblock exercise in Shirvan and Crown Point between 10 am and 2 pm, three people were arrested. A 26-year-old Buccoo man was arrested for using obscene language, while a 25-year-old Bon Accord man was held for driving without a permit, having never been issued one. A 39-year-old Canaan man was also arrested on an outstanding affiliation warrant. Officers issued 21 traffic tickets during that exercise, including 13 for vehicles without inspection stickers, three for having no insurance, two for defective tyres, two for failure to wear seat belts and one for breaching a traffic sign. Meanwhile, Deputy Commissioner of Police (Operations) Suzette Martin has declared that the division is ready for the remainder of Tobago Carnival. "The div... (line truncated to 2000 chars)"""

    EXPECTED_OUTPUT = pd.DataFrame(
        [
            {
                "url": "https://www.guardian.co.tt/news/four-held-for-drunk-driving-in-tobago-6.2.2698647.671a12a8be",
                "content": ARTICLE_1_CONTENT,
            }
        ]
    )

    # Mock HTML response for Guardian article
    MOCK_HTML = f"""<!DOCTYPE html>
<html>
<head><title>Four Held For Drunk Driving In Tobago</title></head>
<body>
<article>
<div class="article-body">
<p>{ARTICLE_1_CONTENT}</p>
</div>
</article>
</body>
</html>"""

    with patch("tt_news_scraper.fetching_utils.articles.requests.get") as mock_get:
        mock_response = type(
            "Response",
            (object,),
            {"ok": True, "text": MOCK_HTML},
        )()
        mock_get.return_value = mock_response

        # call fn
        OBSERVED_OUTPUT = fetch_guardian_article_content(MOCK_INPUT["url"])

        # check for match
        pd.testing.assert_frame_equal(EXPECTED_OUTPUT, OBSERVED_OUTPUT)
