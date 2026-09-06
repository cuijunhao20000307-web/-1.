from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "animex-src")

def must_replace(s, old, new, label, count=1):
    if old not in s:
        raise SystemExit(f"{label} target not found")
    return s.replace(old, new, count)

# Keep existing persisted source IDs and append JAVDAY as mode 4.
p = root / "nxanime_source/provider.hpp"
s = p.read_text()
s = must_replace(
    s,
    """    PROVIDER_SOURCE_KANJU = 3,
};""",
    """    PROVIDER_SOURCE_KANJU = 3,
    // Native HTML provider. Only ordinary public page/media URLs are used.
    PROVIDER_SOURCE_JAVDAY = 4,
};""",
    "provider enum")
p.write_text(s)

p = root / "nxanime_source/provider.cpp"
s = p.read_text()
s = s.replace("g_source_mode > PROVIDER_SOURCE_KANJU", "g_source_mode > PROVIDER_SOURCE_JAVDAY")
s = s.replace("mode > PROVIDER_SOURCE_KANJU", "mode > PROVIDER_SOURCE_JAVDAY")

s = must_replace(
    s,
    '    if (g_source_mode == PROVIDER_SOURCE_KANJU) return "在线电影 · 电影/剧集";',
    '    if (g_source_mode == PROVIDER_SOURCE_KANJU) return "在线电影 · 电影/剧集";\n'
    '    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) return "JAVDAY · 原生播放端";',
    "source name")

s = must_replace(
    s,
    '    if (g_source_mode == PROVIDER_SOURCE_KANJU) return "分类：电影 / 剧集 / 动漫 / 综艺 / 短剧";',
    '    if (g_source_mode == PROVIDER_SOURCE_KANJU) return "分类：电影 / 剧集 / 动漫 / 综艺 / 短剧";\n'
    '    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) return "分类：首页 / 最近更新 · 支持番号搜索";',
    "source endpoint")

s = must_replace(
    s,
    '    if (g_source_mode == PROVIDER_SOURCE_KANJU) return std::string(KANJU_API_BASE) + "/";',
    '    if (g_source_mode == PROVIDER_SOURCE_KANJU) return std::string(KANJU_API_BASE) + "/";\n'
    '    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) return "https://javday.app/";',
    "active referer")

home_sig = """bool provider_fetch_home(const ProxyConfig& proxy,
                         std::vector<AnimeItem>& out,
                         std::string& status) {"""

helper = r'''
static const char* JAVDAY_BASE = "https://javday.app";

static std::string javday_normalize_code(const std::string& query) {
    std::string code;
    code.reserve(query.size());
    for (unsigned char c : query) {
        if (std::isalnum(c)) code.push_back((char)std::toupper(c));
    }
    return code;
}

static std::string javday_attr(const std::string& tag, const char* key) {
    std::string lower = tag;
    std::transform(lower.begin(), lower.end(), lower.begin(),
                   [](unsigned char c){ return (char)std::tolower(c); });
    std::string needle = std::string(key) + "=";
    std::transform(needle.begin(), needle.end(), needle.begin(),
                   [](unsigned char c){ return (char)std::tolower(c); });
    size_t p = lower.find(needle);
    if (p == std::string::npos) return {};
    p += needle.size();
    while (p < tag.size() && std::isspace((unsigned char)tag[p])) ++p;
    if (p >= tag.size()) return {};
    char quote = 0;
    if (tag[p] == '"' || tag[p] == '\'') quote = tag[p++];
    size_t e = p;
    if (quote) {
        e = tag.find(quote, p);
        if (e == std::string::npos) return {};
    } else {
        while (e < tag.size() && !std::isspace((unsigned char)tag[e]) && tag[e] != '>') ++e;
    }
    return tag.substr(p, e - p);
}

static std::string javday_html_unescape(std::string v) {
    auto replace_all = [&](const std::string& a, const std::string& b) {
        size_t p = 0;
        while ((p = v.find(a, p)) != std::string::npos) {
            v.replace(p, a.size(), b);
            p += b.size();
        }
    };
    replace_all("&amp;", "&");
    replace_all("&quot;", "\"");
    replace_all("&#39;", "'");
    replace_all("\\/", "/");
    replace_all("\\u0026", "&");
    return v;
}

static bool javday_http_get(const ProxyConfig& proxy,
                            const std::string& url,
                            std::string& body,
                            long& http_code,
                            std::string& status) {
    body.clear();
    http_code = 0;
    CURL* c = curl_easy_init();
    if (!c) { status = "JAVDAY 网络初始化失败"; return false; }
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8");
    headers = curl_slist_append(headers, "Accept-Language: zh-CN,zh;q=0.9,en;q=0.7");
    headers = curl_slist_append(headers, "Cache-Control: no-cache");
    curl_easy_setopt(c, CURLOPT_URL, url.c_str());
    curl_easy_setopt(c, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(c, CURLOPT_REFERER, "https://javday.app/");
    curl_easy_setopt(c, CURLOPT_USERAGENT,
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36");
    curl_easy_setopt(c, CURLOPT_WRITEFUNCTION, write_cb);
    curl_easy_setopt(c, CURLOPT_WRITEDATA, &body);
    NetworkOptions options;
    options.connect_timeout_seconds = 4;
    options.total_timeout_seconds = 12;
    options.low_speed_seconds = 4;
    options.max_attempts = 2;
    options.network_mode = 0;
    options.allow_ipv4_fallback = proxy.mode == PROXY_MODE_DIRECT;
    network_apply_proxy(c, proxy);
    const NetworkResult result = network_perform_get(
        c, VideoNetworkStage::Api, reset_string_response, &body, options,
        g_provider_cancel);
    http_code = result.http_code;
    curl_slist_free_all(headers);
    curl_easy_cleanup(c);
    if (!result.success()) {
        status = std::string("JAVDAY 请求失败：") + result.error;
        return false;
    }
    if (body.empty()) { status = "JAVDAY 返回空页面"; return false; }
    return true;
}

static std::string javday_meta(const std::string& html, const char* key) {
    size_t p = 0;
    while ((p = html.find("<meta", p)) != std::string::npos) {
        size_t e = html.find('>', p);
        if (e == std::string::npos) break;
        std::string tag = html.substr(p, e - p + 1);
        std::string name = javday_attr(tag, "property");
        if (name.empty()) name = javday_attr(tag, "name");
        std::string low = name;
        std::transform(low.begin(), low.end(), low.begin(),
                       [](unsigned char c){ return (char)std::tolower(c); });
        std::string target = key;
        std::transform(target.begin(), target.end(), target.begin(),
                       [](unsigned char c){ return (char)std::tolower(c); });
        if (low == target) return javday_html_unescape(javday_attr(tag, "content"));
        p = e + 1;
    }
    return {};
}

static std::string javday_title_from_html(const std::string& html) {
    std::string title = javday_meta(html, "og:title");
    if (title.empty()) {
        size_t p = html.find("<title");
        p = p == std::string::npos ? p : html.find('>', p);
        size_t e = p == std::string::npos ? p : html.find("</title>", p + 1);
        if (p != std::string::npos && e != std::string::npos)
            title = strip_html(html.substr(p + 1, e - p - 1));
    }
    const std::string suffix = " - JAVDAY";
    size_t cut = title.rfind(suffix);
    if (cut != std::string::npos) title.resize(cut);
    return trim(javday_html_unescape(title));
}

static std::string javday_slug_from_url(const std::string& url) {
    size_t p = url.find("/videos/");
    if (p == std::string::npos) return {};
    p += 8;
    size_t e = url.find_first_of("/?#", p);
    std::string slug = url.substr(p, e == std::string::npos ? std::string::npos : e - p);
    std::string clean;
    for (unsigned char c : slug)
        if (std::isalnum(c)) clean.push_back((char)std::toupper(c));
    return clean;
}

static void javday_parse_items(const std::string& html,
                               std::vector<AnimeItem>& out,
                               size_t limit = 200) {
    out.clear();
    std::set<std::string> seen;
    size_t p = 0;
    while (p < html.size() && out.size() < limit) {
        size_t v = html.find("/videos/", p);
        if (v == std::string::npos) break;
        size_t a = html.rfind("<a", v);
        if (a == std::string::npos || v - a > 512) { p = v + 8; continue; }
        size_t ae = html.find('>', a);
        if (ae == std::string::npos || ae < v) { p = v + 8; continue; }
        std::string atag = html.substr(a, ae - a + 1);
        std::string href = javday_html_unescape(javday_attr(atag, "href"));
        if (href.find("/videos/") == std::string::npos) { p = ae + 1; continue; }
        std::string page = absolute_url(href, JAVDAY_BASE);
        std::string slug = javday_slug_from_url(page);
        if (slug.empty() || !seen.insert(slug).second) { p = ae + 1; continue; }

        size_t close = html.find("</a>", ae + 1);
        if (close == std::string::npos || close - ae > 8192) close = std::min(html.size(), ae + 4096);
        std::string block = html.substr(a, close - a);

        std::string title = javday_html_unescape(javday_attr(atag, "title"));
        if (title.empty()) {
            std::string text = strip_html(block);
            title = trim(javday_html_unescape(text));
        }
        if (title.empty()) title = slug;

        std::string cover;
        size_t im = block.find("<img");
        if (im != std::string::npos) {
            size_t ie = block.find('>', im);
            if (ie != std::string::npos) {
                std::string itag = block.substr(im, ie - im + 1);
                cover = javday_attr(itag, "data-src");
                if (cover.empty()) cover = javday_attr(itag, "data-original");
                if (cover.empty()) cover = javday_attr(itag, "src");
                cover = absolute_url(javday_html_unescape(cover), JAVDAY_BASE);
            }
        }

        AnimeItem item;
        item.id = "javday:" + slug;
        item.title = title;
        item.url = page;
        item.cover_url = cover;
        item.extra = "JAVDAY · " + slug;
        out.push_back(std::move(item));
        p = close == html.size() ? close : close + 4;
    }
}

static bool javday_fetch_home_native(const ProxyConfig& proxy,
                                     std::vector<AnimeItem>& out,
                                     std::string& status) {
    std::string html;
    long code = 0;
    if (!javday_http_get(proxy, std::string(JAVDAY_BASE) + "/", html, code, status)) return false;
    javday_parse_items(html, out, 200);
    if (out.empty()) {
        status = code == 403 ? "JAVDAY 被站点验证拦截" : "JAVDAY 首页未解析到影片";
        return false;
    }
    status = "JAVDAY 首页 · " + std::to_string(out.size()) + " 条";
    return true;
}

static bool javday_fetch_exact(const ProxyConfig& proxy,
                               const std::string& query,
                               AnimeItem& item,
                               std::string& status) {
    const std::string slug = javday_normalize_code(query);
    if (slug.empty()) { status = "请输入番号，例如 START-551"; return false; }
    const std::string page = std::string(JAVDAY_BASE) + "/videos/" + slug + "/";
    std::string html;
    long code = 0;
    if (!javday_http_get(proxy, page, html, code, status)) return false;
    if (code == 404) { status = "JAVDAY 未找到该番号"; return false; }
    std::string title = javday_title_from_html(html);
    if (title.empty() && html.find("/videos/") == std::string::npos) {
        status = "JAVDAY 详情页格式无法识别";
        return false;
    }
    item = AnimeItem{};
    item.id = "javday:" + slug;
    item.title = title.empty() ? slug : title;
    item.url = page;
    item.cover_url = javday_meta(html, "og:image");
    item.extra = "JAVDAY · " + slug;
    return true;
}

static std::string javday_direct_media(const std::string& html) {
    auto usable = [](const std::string& raw) {
        std::string u = javday_html_unescape(raw);
        if (!starts_with(u, "https://") && !starts_with(u, "http://")) return std::string();
        std::string low = u;
        std::transform(low.begin(), low.end(), low.begin(),
                       [](unsigned char c){ return (char)std::tolower(c); });
        if (low.find(".m3u8") == std::string::npos &&
            low.find(".mp4") == std::string::npos &&
            low.find(".m4v") == std::string::npos) return std::string();
        return u;
    };

    const char* tags[] = {"<source", "<video"};
    for (const char* needle : tags) {
        size_t p = 0;
        while ((p = html.find(needle, p)) != std::string::npos) {
            size_t e = html.find('>', p);
            if (e == std::string::npos) break;
            std::string tag = html.substr(p, e - p + 1);
            std::string u = usable(javday_attr(tag, "src"));
            if (u.empty()) u = usable(javday_attr(tag, "data-src"));
            if (!u.empty()) return u;
            p = e + 1;
        }
    }

    const char* keys[] = {"\"file\"", "\"src\"", "\"url\"", "\"play_url\""};
    for (const char* key : keys) {
        size_t p = 0;
        while ((p = html.find(key, p)) != std::string::npos) {
            p = html.find(':', p + std::strlen(key));
            if (p == std::string::npos) break;
            ++p;
            while (p < html.size() && std::isspace((unsigned char)html[p])) ++p;
            if (p < html.size() && (html[p] == '"' || html[p] == '\'')) {
                char q = html[p++];
                size_t e = p;
                bool esc = false;
                for (; e < html.size(); ++e) {
                    char c = html[e];
                    if (!esc && c == q) break;
                    if (c == '\\' && !esc) esc = true; else esc = false;
                }
                std::string u = usable(html.substr(p, e - p));
                if (!u.empty()) return u;
                p = e;
            }
        }
    }

    size_t p = 0;
    while ((p = html.find("http", p)) != std::string::npos) {
        size_t e = p;
        while (e < html.size() && html[e] != '"' && html[e] != '\'' &&
               html[e] != '<' && html[e] != '>' && !std::isspace((unsigned char)html[e])) ++e;
        std::string u = usable(html.substr(p, e - p));
        if (!u.empty()) return u;
        p = e;
    }
    return {};
}

'''
s = must_replace(s, home_sig, helper + home_sig, "native helper insert")

# Native home branch.
s = must_replace(
    s, home_sig,
    home_sig + """
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY)
        return javday_fetch_home_native(proxy, out, status);""",
    "home branch")

search_page_sig = """bool provider_search_page(const ProxyConfig& proxy,
                          const std::string& query,
                          ProviderSearchPage& continuation,
                          std::vector<AnimeItem>& out,
                          std::string& status) {"""
s = must_replace(
    s, search_page_sig,
    search_page_sig + """
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        out.clear();
        if (!continuation.has_more) { status = "没有更多结果"; return true; }
        AnimeItem item;
        if (!javday_fetch_exact(proxy, query, item, status)) return false;
        out.push_back(std::move(item));
        continuation.has_more = false;
        continuation.page = 2;
        continuation.offset = 1;
        status = "JAVDAY 搜索完成 · 1 条";
        return true;
    }""",
    "search page branch")

search_sig = """bool provider_search(const ProxyConfig& proxy,
                     const std::string& query,
                     std::vector<AnimeItem>& out,
                     std::string& status) {"""
s = must_replace(
    s, search_sig,
    search_sig + """
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        if (query.empty()) return javday_fetch_home_native(proxy, out, status);
        out.clear();
        AnimeItem item;
        if (!javday_fetch_exact(proxy, query, item, status)) return false;
        out.push_back(std::move(item));
        status = "JAVDAY 番号搜索 · 1 条";
        return true;
    }""",
    "search branch")

filter_sig = """bool provider_filter(const ProxyConfig& proxy,
                     int channel_id,
                     const std::string& genre,
                     const std::string& quarter,
                     const std::string& year,
                     const std::string& language,
                     const std::string& sort_by,
                     std::vector<AnimeItem>& out,
                     std::string& status) {"""
s = must_replace(
    s, filter_sig,
    filter_sig + """
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        (void)channel_id; (void)genre; (void)quarter; (void)year;
        (void)language; (void)sort_by;
        return javday_fetch_home_native(proxy, out, status);
    }""",
    "filter branch")

detail_sig = """bool provider_fetch_detail(const ProxyConfig& proxy,
                           const AnimeItem& item,
                           AnimeDetail& out,
                           std::string& status) {"""
s = must_replace(
    s, detail_sig,
    detail_sig + """
    if (starts_with(item.id, "javday:")) {
        std::string html;
        long http = 0;
        if (!javday_http_get(proxy, item.url, html, http, status)) return false;
        out = AnimeDetail{};
        out.id = item.id;
        out.title = javday_title_from_html(html);
        if (out.title.empty()) out.title = item.title;
        out.status = "JAVDAY 原生播放端";
        out.description = javday_meta(html, "description");
        out.url = item.url;
        out.cover_url = javday_meta(html, "og:image");
        if (out.cover_url.empty()) out.cover_url = item.cover_url;
        std::string slug = item.id.substr(std::strlen("javday:"));
        out.episodes.push_back({"播放", "javday://play/" + slug});
        status = "JAVDAY 详情完成 · 1 个播放入口";
        return true;
    }""",
    "detail branch")

resolve_sig = """bool provider_resolve_special_episode(const ProxyConfig& proxy,
                                      const EpisodeItem& episode,
                                      std::string& media_url,
                                      std::string& referer,
                                      std::string& status,
                                      bool& handled,
                                      const std::vector<std::string>* rejected) {"""
s = must_replace(
    s, resolve_sig,
    resolve_sig + """
    if (starts_with(episode.url, "javday://play/")) {
        handled = true;
        media_url.clear();
        const std::string slug = javday_normalize_code(
            episode.url.substr(std::strlen("javday://play/")));
        if (slug.empty()) { status = "JAVDAY 播放参数无效"; return false; }
        const std::string page = std::string(JAVDAY_BASE) + "/videos/" + slug + "/";
        std::string html;
        long http = 0;
        if (!javday_http_get(proxy, page, html, http, status)) return false;
        media_url = javday_direct_media(html);
        if (media_url.empty()) {
            status = "JAVDAY 页面未公开可直接播放的 m3u8/mp4 地址";
            return false;
        }
        if (rejected && std::find(rejected->begin(), rejected->end(), media_url) != rejected->end()) {
            status = "JAVDAY 当前公开线路已尝试";
            return false;
        }
        referer = page;
        status = "JAVDAY 公开播放地址已解析";
        return true;
    }""",
    "resolver branch")

test_sig = """bool provider_test_source(const ProxyConfig& proxy, std::string& status) {"""
s = must_replace(
    s, test_sig,
    test_sig + """
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        std::vector<AnimeItem> items;
        if (!javday_fetch_home_native(proxy, items, status)) return false;
        status = "JAVDAY 原生播放端正常 · " + std::to_string(items.size()) + " 条";
        return true;
    }""",
    "test branch")

p.write_text(s)

# Launcher: expose JAVDAY as a normal provider, no WebApplet/browser path.
p = root / "nxanime_source/main.cpp"
s = p.read_text()
s = must_replace(
    s,
    """static void launcher_cycle_source(State& st,int dir){
    const int source_order[]={PROVIDER_SOURCE_BUILTIN,PROVIDER_SOURCE_RRTV,
                              PROVIDER_SOURCE_KANJU,PROVIDER_SOURCE_CUSTOM};
    int current=0;
    for(int i=0;i<4;++i)if(source_order[i]==provider_source_mode()){current=i;break;}
    int mode=source_order[wrapi(current+dir,4)];std::string msg;""",
    """static void launcher_cycle_source(State& st,int dir){
    const int source_order[]={PROVIDER_SOURCE_BUILTIN,PROVIDER_SOURCE_RRTV,
                              PROVIDER_SOURCE_KANJU,PROVIDER_SOURCE_JAVDAY,
                              PROVIDER_SOURCE_CUSTOM};
    int current=0;
    for(int i=0;i<5;++i)if(source_order[i]==provider_source_mode()){current=i;break;}
    int mode=source_order[wrapi(current+dir,5)];std::string msg;""",
    "launcher order")

s = must_replace(
    s,
    'safe_text(b,s,210,184,2,provider_source_mode()==1?"ONLINE VIDEO":provider_source_mode()==2?"CUSTOM DATA":provider_source_mode()==3?"ONLINE MOVIE 2":"ONLINE ANIME",white);',
    'safe_text(b,s,210,184,2,provider_source_mode()==1?"ONLINE VIDEO":provider_source_mode()==2?"CUSTOM DATA":provider_source_mode()==3?"ONLINE MOVIE 2":provider_source_mode()==4?"JAVDAY NATIVE":"ONLINE ANIME",white);',
    "launcher label")
p.write_text(s)
