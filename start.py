import markdown
from bs4 import BeautifulSoup
from flask import Flask, render_template, redirect, request, url_for
import requests

from params import MULTICASE_URL

app = Flask(__name__)


@app.route("/")
def main():
    return render_template("index.html")


@app.route("/jira_request", methods=["POST"])
def jira_request_handler():
    request_name = request.form["request_name"]

    if request_name == "case_author":
        return redirect(url_for(request_name))

    elif request_name == "case_replies":
        return redirect(url_for(request_name))


@app.route("/jira_request/case_author")
def case_author():
    import json
    # mc = "M000733"
    # res = requests.get('{}/author/{}'.format(MULTICASE_URL, mc), headers={'user-token': ''})
    # author = res.json()
    # author_name = author["fullname"]
    # author_email = author["email"]

    url = 'https://support.mededtech.ru/rest/api/2/search'

    headers = {
        "Accept": "application/json",
    }

    params = {
        # "jql": 'status = Доработка and created>="2019/05/09"'
        # key = "MT-815" or key = "MT-816"
        "jql": 'key=MT-815'
    }
    response = requests.request(
        "GET",
        url,
        headers=headers,
        params=params,
        auth=("login", "password")
    )

    res = response.json()
    issues = res["issues"]
    mc_codes_info = {}  # Полная информация о кейсе
    issues_info = {}  # Полная информация о задаче

    for issue in issues:
        # print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
        issue_key = issue["key"]
        issues_info[issue_key] = {
            "mc_code": "",
            "mc_author": "",
            "status": u"Доработка",
            "description": issue["fields"]["description"],
            "comments": ""}

        code = issue["fields"]["customfield_10301"]  # Код мультикейса
        issues_info[issue_key]["mc_code"] = code
        # issues_info[issue_key]["mc_author"] = get_author(code)
        issues_info[issue_key]["comments"] = get_issue_comments(issue_key)

        # if not code in mc_codes_info:
        #     mc_codes_info[code] = {"issues": [],
        #                            "author": {
        #                                "fullname": "",
        #                                "email": ""
        #                            }}
        # mc_codes_info[code]["issues"].append(issue["key"])

    # for code in mc_codes_info:
    #     author = requests.get('{}/author/{}'.format(MULTICASE_URL, code), headers={'user-token': 'publish_btz'})
    #     author = author.json()
    #     mc_codes_info[code]["author"]["fullname"] = author["fullname"]
    #     mc_codes_info[code]["author"]["email"] = author["email"]

    return render_template("case_author.html", issues_info=issues_info)


@app.route("/jira_request/case_replies")
def case_replies():
    import json

    # url = "https://support.mededtech.ru/rest/servicedeskapi/servicedesk/2"

    jql = """
            SELECT 
 link(jql.issue, '_blank') AS "Issue"
FROM 
 JQL
WHERE
 jql.query='issuekey ="MT-977"'
    """

    url = 'https://support.mededtech.ru/rest/api/2/issue/picker'
    url = 'https://support.mededtech.ru/rest/api/2/search'

    headers = {
        "Accept": "application/json",
    }

    params = {
        "jql": 'status=Доработка"'
    }
    response = requests.request(
        "GET",
        url,
        headers=headers,
        params=params,
        auth=("login", "password")
    )

    res = response.json()
    issues = res["issues"]
    print(issues)
    mc_codes = {}

    for issue in issues:
        code = issue["fields"]["customfield_10301"]
        if not code in mc_codes:
            mc_codes[code] = []
        mc_codes[code].append(issue["key"])

    for code in mc_codes:
        author = requests.get('{}/author/{}'.format(MULTICASE_URL, code), headers={'user-token': ''})

        author = author.json()
        mc_codes[code]["author"] = {}
        mc_codes[code]["author"]["fullname"] = author["fullname"]
        mc_codes[code]["author"]["email"] = author["email"]

    #
    # print (issue_keys, res.json())
    # print(json.dumps(json.loads(response.text)["issues"], sort_keys=True, indent=4, separators=(",", ": ")))
    # print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))

    return render_template("case_replies.html")


def get_author(mc_code):
    author = requests.get('{}/author/{}'.format(MULTICASE_URL, mc_code), headers={'user-token': ''})
    author = author.json()
    author_dict = {"fullname": author["fullname"],
                   "email": author["email"]}

    return author_dict


def get_issue_comments(issue_key):
    import json
    url = f"https://support.mededtech.ru/rest/api/2/issue/{issue_key}/comment"

    headers = {
        "Accept": "application/json",
    }

    response = requests.request(
        "GET",
        url,
        headers=headers,
        auth=("login", "password")
    )

    comments = json.loads(response.text)["comments"]
    comments_text = ""

    for comment in comments:
        # if comment["author"]["displayName"] == "userName":
        #     continue
        # html = markdown.markdown(comment["body"])
        # comments_text += html
        comments_text += comment["body"]
    # print(json.dumps(json.loads(response.text)["comments"], sort_keys=True, indent=4, separators=(",", ": ")))

    return comments_text


@app.route("/send_mail", methods=["POST"])
def send_email():
    import smtplib
    from email.mime.text import MIMEText

    HOST = "smtp.gmail.com"
    SUBJECT = "Test html"
    TO = "mail"
    FROM = "mail"

    msg_content = "<b>Замечание:</b></br>"
    msg_content += markdown.markdown(request.form['description'])
    msg_content += "<b>Комментарии:</b></br>"

    # msg_content += markdown.markdown(request.form['comments'].replace("#", "+"))
    msg_content += render_markdown(request.form['comments'].replace("#", "-"))
    print(msg_content)
    message = MIMEText(msg_content, 'html')
    message['From'] = FROM
    message['To'] = TO
    message['Subject'] = SUBJECT

    # Работает
    server = smtplib.SMTP(HOST, 587)
    server.ehlo()
    server.starttls()
    server.login('login', "password")
    server.sendmail(FROM, [TO], message.as_string())
    server.close()

    return ""


def render_markdown(text):
    import bleach
    if not text:
        return ''

    html = markdown.markdown(text, extensions=[
        'markdown.extensions.sane_lists',
        'markdown.extensions.nl2br',
    ])
    return bleach.clean(html, tags=[
        'p', 'h1', 'h2', 'br', 'h3', 'b', 'strong', 'u', 'i', 'em', 'hr', 'ul', 'ol', 'li', 'blockquote'
    ])


@app.route("/connect_cases", methods=["POST"])
def connect_cases():
    import json
    url = 'https://support.mededtech.ru/rest/api/2/search'

    headers = {
        "Accept": "application/json",
    }

    params = {
         # "jql": 'key in(MT-815, MT-1091, MT-1092)',
        # key = "MT-815" or key = "MT-816"
        "jql": 'status=Доработка and project="Отзывы о мультикейсах"',
        "maxResults": 10000000


    }
    response = requests.request(
        "GET",
        url,
        headers=headers,
        params=params,
        auth=("login", "password")
    )

    res = response.json()
    issues = res["issues"]
    mc_codes_info = {}  # Полная информация о кейсе
    issues_info = {}  # Полная информация о задаче

    for issue in issues:
        issue_key = issue["key"]
        code = issue["fields"]["customfield_10301"]  # Код мультикейса
        if not code in mc_codes_info:
            mc_codes_info[code] = {"issues": [],
                                   }
        mc_codes_info[code]["issues"].append({"key": issue_key,
                                              "created": issue["fields"]["created"]})
    # mc_codes_info = sorted(mc_codes_info.keys())
    for code in sorted(mc_codes_info.keys()):
        issues = mc_codes_info[code]["issues"]
        ordered_issues = sorted(issues, key=lambda k: k['created'])
        connect_issues(ordered_issues[0]["key"], ordered_issues[1:], code)

    return "Кейсы связаны"


def connect_issues(outwardIssue, inwardIssues, mc_code):
    from jira import JIRA

    options = {
        'server': 'https://support...ru'}

    # jira = JIRA(options, basic_auth=("login", "password"))
    #
    # link_type = "связана"
    # for issue in inwardIssues:
    #     inwardIssue = issue["key"]
    #     jira.create_issue_link(link_type,inwardIssue, outwardIssue)
    #     # print(outwardIssue)
    #     print (f"Case {outwardIssue} linked with {inwardIssue}, {mc_code}")
