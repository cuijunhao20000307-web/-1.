from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "animex-src")

def must_replace(s, old, new, label, count=1):
    if old not in s:
        raise SystemExit(f"{label} target not found")
    return s.replace(old, new, count)

# provider.hpp: append source mode 4, preserving old persisted IDs.
p = root / "nxanime_source/provider.hpp"
s = p.read_text()
s = must_replace(
    s,
    """    PROVIDER_SOURCE_KANJU = 3,
};""",
    """    PROVIDER_SOURCE_KANJU = 3,
    // External web source. Pages are opened with the system WebApplet;
    // ANIMEX does not extract or bypass the site's media URLs.
    PROVIDER_SOURCE_JAVDAY = 4,
};""",
    "provider enum",
)
p.write_text(s)

# provider.cpp: source metadata and external-page records.
p = root / "nxanime_source/provider.cpp"
s = p.read_text()
s = s.replace("g_source_mode > PROVIDER_SOURCE_KANJU", "g_source_mode > PROVIDER_SOURCE_JAVDAY")
s = s.replace("mode > PROVIDER_SOURCE_KANJU", "mode > PROVIDER_SOURCE_JAVDAY")

s = must_replace(
    s,
    """std::string provider_source_name() {
    if (g_source_mode == PROVIDER_SOURCE_RRTV) return "在线影视 · 剧集/综艺";
    if (g_source_mode == PROVIDER_SOURCE_CUSTOM) return "自定义源 · MacCMS/API";
    if (g_source_mode == PROVIDER_SOURCE_KANJU) return "在线电影 · 电影/剧集";
    return "在线动漫 · 番剧/动画";
}""",
    """std::string provider_source_name() {
    if (g_source_mode == PROVIDER_SOURCE_RRTV) return "在线影视 · 剧集/综艺";
    if (g_source_mode == PROVIDER_SOURCE_CUSTOM) return "自定义源 · MacCMS/API";
    if (g_source_mode == PROVIDER_SOURCE_KANJU) return "在线电影 · 电影/剧集";
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) return "JAVDAY · 外部网页";
    return "在线动漫 · 番剧/动画";
}""",
    "source name",
)

s = must_replace(
    s,
    """std::string provider_source_endpoint() {
    if (g_source_mode == PROVIDER_SOURCE_RRTV) return "分类：电视剧 / 综艺 / 纪录片 / 影视";
    if (g_source_mode == PROVIDER_SOURCE_CUSTOM)
        return g_custom_api_base.empty() ? "分类：自定义 · 按 X 输入网站/API" : "分类：自定义 · 网站/API 已配置";
    if (g_source_mode == PROVIDER_SOURCE_KANJU) return "分类：电影 / 剧集 / 动漫 / 综艺 / 短剧";
    return "分类：新番 / 热门 / 日语 / 国语 / 热血 / 剧场版";
}""",
    """std::string provider_source_endpoint() {
    if (g_source_mode == PROVIDER_SOURCE_RRTV) return "分类：电视剧 / 综艺 / 纪录片 / 影视";
    if (g_source_mode == PROVIDER_SOURCE_CUSTOM)
        return g_custom_api_base.empty() ? "分类：自定义 · 按 X 输入网站/API" : "分类：自定义 · 网站/API 已配置";
    if (g_source_mode == PROVIDER_SOURCE_KANJU) return "分类：电影 / 剧集 / 动漫 / 综艺 / 短剧";
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) return "外部入口 · 搜索番号后使用系统网页打开";
    return "分类：新番 / 热门 / 日语 / 国语 / 热血 / 剧场版";
}""",
    "source endpoint",
)

s = must_replace(
    s,
    """std::string provider_active_referer() {
    if (g_source_mode == PROVIDER_SOURCE_RRTV) return std::string(RRTV_SITE_BASE) + "/";
    if (g_source_mode == PROVIDER_SOURCE_KANJU) return std::string(KANJU_API_BASE) + "/";
    if (g_source_mode == PROVIDER_SOURCE_CUSTOM && !g_custom_api_base.empty())
        return g_custom_api_base + "/";
    return "https://ani.girigirilove.com/";
}""",
    """std::string provider_active_referer() {
    if (g_source_mode == PROVIDER_SOURCE_RRTV) return std::string(RRTV_SITE_BASE) + "/";
    if (g_source_mode == PROVIDER_SOURCE_KANJU) return std::string(KANJU_API_BASE) + "/";
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) return "https://javday.app/";
    if (g_source_mode == PROVIDER_SOURCE_CUSTOM && !g_custom_api_base.empty())
        return g_custom_api_base + "/";
    return "https://ani.girigirilove.com/";
}""",
    "active referer",
)

home_sig = """bool provider_fetch_home(const ProxyConfig& proxy,
                         std::vector<AnimeItem>& out,
                         std::string& status) {"""
helper = r'''static std::string javday_normalize_code(const std::string& query) {
    std::string code;
    code.reserve(query.size());
    for (unsigned char c : query) {
        if (std::isalnum(c)) code.push_back((char)std::toupper(c));
    }
    return code;
}

static AnimeItem javday_make_item(const std::string& query) {
    const std::string code = javday_normalize_code(query);
    AnimeItem item;
    item.id = "javday:" + code;
    item.title = code.empty() ? "JAVDAY · 使用搜索输入番号" : "JAVDAY · " + code;
    item.url = code.empty()
        ? "https://javday.app/"
        : "https://javday.app/videos/" + code + "/";
    item.extra = "外部网页入口 · 使用系统 WebApplet 打开";
    return item;
}

'''
if helper not in s:
    s = must_replace(s, home_sig, helper + home_sig, "home helper insert")

s = must_replace(
    s,
    """bool provider_fetch_home(const ProxyConfig& proxy,
                         std::vector<AnimeItem>& out,
                         std::string& status) {
    if (g_source_mode == PROVIDER_SOURCE_RRTV) return rrtv_fetch_featured_200(proxy, out, status);
    if (g_source_mode == PROVIDER_SOURCE_KANJU) return kanju_fetch_home(proxy, out, status);""",
    """bool provider_fetch_home(const ProxyConfig& proxy,
                         std::vector<AnimeItem>& out,
                         std::string& status) {
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        (void)proxy;
        out.clear();
        out.push_back(javday_make_item(""));
        status = "JAVDAY 外部入口 · 使用搜索输入番号";
        return true;
    }
    if (g_source_mode == PROVIDER_SOURCE_RRTV) return rrtv_fetch_featured_200(proxy, out, status);
    if (g_source_mode == PROVIDER_SOURCE_KANJU) return kanju_fetch_home(proxy, out, status);""",
    "home source branch",
)

s = must_replace(
    s,
    """bool provider_search_page(const ProxyConfig& proxy,
                          const std::string& query,
                          ProviderSearchPage& continuation,
                          std::vector<AnimeItem>& out,
                          std::string& status) {
    if(g_source_mode==PROVIDER_SOURCE_KANJU)
        return provider_movie_search_page(proxy,query,continuation,out,status);""",
    """bool provider_search_page(const ProxyConfig& proxy,
                          const std::string& query,
                          ProviderSearchPage& continuation,
                          std::vector<AnimeItem>& out,
                          std::string& status) {
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        (void)proxy;
        out.clear();
        const std::string code = javday_normalize_code(query);
        if (code.empty()) { status = "请输入番号，例如 START-551"; return false; }
        if (!continuation.has_more) { status = "没有更多结果"; return true; }
        out.push_back(javday_make_item(query));
        continuation.has_more = false;
        continuation.page = 2;
        continuation.offset = 1;
        status = "JAVDAY 番号入口 · " + code;
        return true;
    }
    if(g_source_mode==PROVIDER_SOURCE_KANJU)
        return provider_movie_search_page(proxy,query,continuation,out,status);""",
    "search page",
)

s = must_replace(
    s,
    """bool provider_search(const ProxyConfig& proxy,
                     const std::string& query,
                     std::vector<AnimeItem>& out,
                     std::string& status) {
    if (query.empty()) return provider_fetch_home(proxy, out, status);""",
    """bool provider_search(const ProxyConfig& proxy,
                     const std::string& query,
                     std::vector<AnimeItem>& out,
                     std::string& status) {
    if (query.empty()) return provider_fetch_home(proxy, out, status);
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        (void)proxy;
        out.clear();
        const std::string code = javday_normalize_code(query);
        if (code.empty()) { status = "请输入番号，例如 START-551"; return false; }
        out.push_back(javday_make_item(query));
        status = "JAVDAY 番号入口 · " + code;
        return true;
    }""",
    "search",
)

s = must_replace(
    s,
    """bool provider_filter(const ProxyConfig& proxy,
                     int channel_id,
                     const std::string& genre,
                     const std::string& quarter,
                     const std::string& year,
                     const std::string& language,
                     const std::string& sort_by,
                     std::vector<AnimeItem>& out,
                     std::string& status) {
    if (g_source_mode == PROVIDER_SOURCE_KANJU) {""",
    """bool provider_filter(const ProxyConfig& proxy,
                     int channel_id,
                     const std::string& genre,
                     const std::string& quarter,
                     const std::string& year,
                     const std::string& language,
                     const std::string& sort_by,
                     std::vector<AnimeItem>& out,
                     std::string& status) {
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        (void)channel_id; (void)genre; (void)quarter; (void)year; (void)language; (void)sort_by;
        return provider_fetch_home(proxy, out, status);
    }
    if (g_source_mode == PROVIDER_SOURCE_KANJU) {""",
    "filter",
)

s = must_replace(
    s,
    """bool provider_fetch_detail(const ProxyConfig& proxy,
                           const AnimeItem& item,
                           AnimeDetail& out,
                           std::string& status) {
    if (starts_with(item.id, "kanju:") || starts_with(item.url, "kanju://"))""",
    """bool provider_fetch_detail(const ProxyConfig& proxy,
                           const AnimeItem& item,
                           AnimeDetail& out,
                           std::string& status) {
    if (starts_with(item.id, "javday:")) {
        (void)proxy;
        out = AnimeDetail{};
        out.id = item.id;
        out.title = item.title;
        out.status = "JAVDAY 外部网页";
        out.description = "ANIMEX 不提取该站点的隐藏播放地址；按 A 使用 Nintendo Switch 系统 WebApplet 打开页面。";
        out.url = item.url;
        out.episodes.push_back({"打开网页", "webapp://" + item.url});
        status = "JAVDAY 外部入口已准备";
        return true;
    }
    if (starts_with(item.id, "kanju:") || starts_with(item.url, "kanju://"))""",
    "detail",
)

s = must_replace(
    s,
    """bool provider_test_source(const ProxyConfig& proxy, std::string& status) {
    if (g_source_mode == PROVIDER_SOURCE_KANJU) {""",
    """bool provider_test_source(const ProxyConfig& proxy, std::string& status) {
    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        (void)proxy;
        status = "JAVDAY 外部入口已配置 · 页面由系统 WebApplet 打开";
        return true;
    }
    if (g_source_mode == PROVIDER_SOURCE_KANJU) {""",
    "test source",
)
p.write_text(s)

# main.cpp: launcher entry + system WebApplet dispatch.
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
    "launcher source order",
)

s = must_replace(
    s,
    'safe_text(b,s,210,184,2,provider_source_mode()==1?"ONLINE VIDEO":provider_source_mode()==2?"CUSTOM DATA":provider_source_mode()==3?"ONLINE MOVIE 2":"ONLINE ANIME",white);',
    'safe_text(b,s,210,184,2,provider_source_mode()==1?"ONLINE VIDEO":provider_source_mode()==2?"CUSTOM DATA":provider_source_mode()==3?"ONLINE MOVIE 2":provider_source_mode()==4?"JAVDAY WEB":"ONLINE ANIME",white);',
    "safe launcher label",
)

play_sig = """static void play_current_episode(State& st,Framebuffer& fb,PadState& pad){"""
web_helper = r'''static bool open_external_web_page(State& st,Framebuffer& fb,const std::string& url){
    if(url.rfind("https://",0)!=0&&url.rfind("http://",0)!=0){
        st.status="外部网页地址无效";return false;
    }
    stop_home_cover_loader(st);
    WebCommonConfig config{};
    Result rc=webPageCreate(&config,url.c_str());
    if(R_FAILED(rc)){
        char t[128];snprintf(t,sizeof(t),"系统网页初始化失败 · 0x%08X",rc);st.status=t;
        ensure_current_cover(st,fb);return false;
    }
    rc=webConfigShow(&config,nullptr);
    if(R_FAILED(rc)){
        char t[128];snprintf(t,sizeof(t),"系统网页打开失败 · 0x%08X",rc);st.status=t;
        ensure_current_cover(st,fb);return false;
    }
    st.status="已从外部网页返回";
    ensure_current_cover(st,fb);
    return true;
}

'''
if web_helper not in s:
    s = must_replace(s, play_sig, web_helper + play_sig, "web helper insert")

s = must_replace(
    s,
    """        const EpisodeItem epitem=st.detail.episodes[st.ep];
        st.screen=EPISODE;
        st.status="视频正在缓冲中";""",
    """        const EpisodeItem epitem=st.detail.episodes[st.ep];
        if(epitem.url.rfind("webapp://",0)==0){
            const std::string page_url=epitem.url.substr(9);
            st.screen=DETAIL;
            st.status="正在打开系统网页...";
            draw_frame(fb,st);
            open_external_web_page(st,fb,page_url);
            return;
        }
        st.screen=EPISODE;
        st.status="视频正在缓冲中";""",
    "webapp playback interception",
)
p.write_text(s)
