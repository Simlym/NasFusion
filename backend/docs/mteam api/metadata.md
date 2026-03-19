
1.查看站点信息
Request URL：https://api.m-team.io/api/system/state
Request Method：post
Payload：空
响应示例：
{
    "code": "0",
    "message": "SUCCESS",
    "data": {
        "userMax": "150000",
        "userCount": "94835",
        "todayUserCount": "21855",
        "weekUserCount": "59564",
        "paddingUserCount": "0",
        "warnUserCount": "546",
        "banUserCount": "253",
        "torrentCount": "631585",
        "dieTorrentCount": "3046",
        "peerCount": "17474596",
        "seederCount": "17361960",
        "leecherCount": "112636",
        "peerUserCount": "65476",
        "currentUserCount": "983",
        "torrentSizeSum": "16991325548821226",
        "uploadSum": "3330188318929367481",
        "downloadSum": "4851200059251841749",
        "flowSum": "8181388378181209230"
    }
}

2.站点类别
Request URL：https://api.m-team.io/api/torrent/categoryList
Request Method：POST
Payload：空
响应示例：
{
    "code": "0",
    "message": "SUCCESS",
    "data": {
        "list": [
            {
                "createdDate": "2024-03-22 14:00:15",
                "lastModifiedDate": "2024-03-26 23:50:33",
                "id": "100",
                "order": "1",
                "nameChs": "电影",
                "nameCht": "電影",
                "nameEng": "Movie",
                "image": "",
                "parent": null
            },
            {
                "createdDate": "2024-03-22 14:00:15",
                "lastModifiedDate": "2024-05-22 13:05:21",
                "id": "423",
                "order": "1",
                "nameChs": "PC游戏",
                "nameCht": "PC遊戲",
                "nameEng": "PCGame",
                "image": "game-pc-3.jpeg",
                "parent": "447"
            },
            {
                "createdDate": "2024-03-22 14:00:15",
                "lastModifiedDate": "2024-03-22 14:00:15",
                "id": "440",
                "order": "440",
                "nameChs": "AV(Gay)/HD",
                "nameCht": "AV(Gay)/HD",
                "nameEng": "AV(Gay)/HD",
                "image": "gayhd.gif",
                "parent": "120"
            }
        ],
        "tvshow": [
            "403",
            "402",
            "435",
            "438"
        ],
        "adult": [
            "410",
            "429",
            "424",
            "430",

            "412",
            "413",
            "440"
        ],
        "waterfall": [
            "410",
            "401",
            "419",
            "420",

            "431",
            "437",
            "426",
            "429",

            "441",
            "442",
            "448"
        ],
        "movie": [
            "401",
            "419",
            "420",
            "421",
            "439"
        ],
        "music": [
            "406",
            "434"
        ]
    }
}


URL:https://api.m-team.io/api/torrent/videoCodecList
Request Method：POST
Payload：空
响应示例：{
    "code": "0",
    "message": "SUCCESS",
    "data": [
        {
            "createdDate": "2024-03-22 14:00:15",
            "lastModifiedDate": "2024-05-23 20:55:17",
            "id": "1",
            "order": "1",
            "name": "H.264(x264/AVC)"
        },
        {
            "createdDate": "2024-03-22 14:00:15",
            "lastModifiedDate": "2024-05-23 20:55:21",
            "id": "16",
            "order": "2",
            "name": "H.265(x265/HEVC)"
        },
        {
            "createdDate": "2024-03-22 14:00:15",
            "lastModifiedDate": "2024-06-06 10:10:56",
            "id": "2",
            "order": "3",
            "name": "VC-1"
        },
        {
            "createdDate": "2024-03-22 14:00:15",
            "lastModifiedDate": "2024-05-23 20:38:31",
            "id": "4",
            "order": "7",
            "name": "MPEG-2"
        },
        {
            "createdDate": "2024-06-24 18:42:24",
            "lastModifiedDate": "2024-06-24 18:42:24",
            "id": "22",
            "order": "11",
            "name": "AVS"
        }
    ]
}


URL:https://api.m-team.io/api/torrent/standardList
Request Method：POST
Payload：空
响应示例：
{
    "code": "0",
    "message": "SUCCESS",
    "data": [
        {
            "createdDate": "2024-03-22 14:00:15",
            "lastModifiedDate": "2024-05-23 20:45:22",
            "id": "1",
            "order": "1",
            "name": "1080p"
        },
        {
            "createdDate": "2024-05-23 20:45:11",
            "lastModifiedDate": "2024-05-23 20:45:41",
            "id": "7",
            "order": "6",
            "name": "8K"
        }
    ]
}

URL:https://api.m-team.io/api/torrent/sourceList
Request Method：POST
Payload：空
响应示例：
{
    "code": "0",
    "message": "SUCCESS",
    "data": [
        {
            "createdDate": "2024-03-27 11:58:33",
            "lastModifiedDate": "2024-05-23 20:47:24",
            "id": "8",
            "order": "1",
            "nameChs": "Web-DL",
            "nameCht": "Web-DL",
            "nameEng": "Web-DL"
        },
        {
            "createdDate": "2025-07-06 21:29:17",
            "lastModifiedDate": "2025-07-06 21:29:17",
            "id": "10",
            "order": "7",
            "nameChs": "CD",
            "nameCht": "CD",
            "nameEng": "CD"
        },
        {
            "createdDate": "2024-03-22 14:00:15",
            "lastModifiedDate": "2024-05-23 20:48:03",
            "id": "6",
            "order": "99",
            "nameChs": "Other",
            "nameCht": "Other",
            "nameEng": "Other"
        }
    ]
}

URL:https://api.m-team.io/api/system/langs
Request Method：POST
Payload：空
响应示例：
{
    "code": "0",
    "message": "SUCCESS",
    "data": [
        {
            "createdDate": "2024-03-22 14:00:13",
            "lastModifiedDate": "2024-03-22 14:00:13",
            "id": "16",
            "langName": "한국어",
            "flagpic": "southkorea.gif",
            "subLang": true,
            "siteLang": false,
            "langTag": null
        },
        {
            "createdDate": "2024-03-22 14:00:13",
            "lastModifiedDate": "2024-03-22 14:00:13",
            "id": "29",
            "langName": "Turkish",
            "flagpic": "turkey.gif",
            "subLang": false,
            "siteLang": false,
            "langTag": null
        },
        {
            "createdDate": "2024-03-22 14:00:13",
            "lastModifiedDate": "2024-03-22 14:00:13",
            "id": "28",
            "langName": "繁體中文",
            "flagpic": "tw.png",
            "subLang": true,
            "siteLang": true,
            "langTag": "zh_TW"
        }
    ]
}

URL:https://api.m-team.io/api/system/countryList
Request Method：POST
Payload：空
响应示例：
{
    "code": "0",
    "message": "SUCCESS",
    "data": [
        {
            "createdDate": "2024-06-11 07:32:46",
            "lastModifiedDate": "2024-06-11 07:32:46",
            "id": "173",
            "name": "Bolivia",
            "pic": "bolivia.gif"
        },
        {
            "createdDate": "2024-03-22 14:00:13",
            "lastModifiedDate": "2024-03-22 14:00:13",
            "id": "107",
            "name": "Pirates",
            "pic": "jollyroger.gif"
        },
        {
            "createdDate": "2024-03-22 14:00:13",
            "lastModifiedDate": "2024-03-22 14:00:13",
            "id": "108",
            "name": "台灣, 中國",
            "pic": "tw.png"
        }
    ]
}


