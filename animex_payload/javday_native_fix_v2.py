from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "animex-src")

def must_replace(s, old, new, label, count=1):
    if old not in s:
        raise SystemExit(f"{label} target not found")
    return s.replace(old, new, count)

# ---------------------------------------------------------------------------
# provider.cpp: parse JAVDAY's current card markup, categories, and public HLS.
# ---------------------------------------------------------------------------
p = root / "nxanime_source/provider.cpp"
s = p.read_text()

old = r'''        std::string title = javday_html_unescape(javday_attr(atag, "title"));
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
'''

new = r'''        std::string title = javday_html_unescape(javday_attr(atag, "title"));
        if (title.empty()) {
            // Current JAVDAY cards keep the actual title in:
            // <span class="title">...</span>
            size_t tc = block.find("class=\"title\"");
            if (tc == std::string::npos) tc = block.find("class='title'");
            if (tc != std::string::npos) {
                size_t tb = block.find('>', tc);
                size_t te = tb == std::string::npos ? std::string::npos : block.find("</span>", tb + 1);
                if (tb != std::string::npos && te != std::string::npos)
                    title = trim(javday_html_unescape(strip_html(block.substr(tb + 1, te - tb - 1))));
            }
        }
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
            }
        }
        // Current homepage uses CSS background-image instead of <img>.
        if (cover.empty()) {
            size_t bg = block.find("background-image");
            if (bg != std::string::npos) {
                size_t ub = block.find("url(", bg);
                if (ub != std::string::npos) {
                    ub += 4;
                    size_t ue = block.find(')', ub);
                    if (ue != std::string::npos) {
                        cover = trim(block.substr(ub, ue - ub));
                        if (cover.size() >= 2 &&
                            ((cover.front() == '"' && cover.back() == '"') ||
                             (cover.front() == '\'' && cover.back() == '\'')))
                            cover = cover.substr(1, cover.size() - 2);
                    }
                }
            }
        }
        cover = absolute_url(javday_html_unescape(cover), JAVDAY_BASE);
'''
s = must_replace(s, old, new, "JAVDAY card parser")

old = r'''static bool javday_fetch_home_native(const ProxyConfig& proxy,
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
'''

new = r'''static const char* javday_category_path(int channel_id) {
    switch (channel_id) {
        case 3001: return "/label/new/";
        case 3002: return "/label/hot/";
        case 3003: return "/category/new-release/";
        case 3004: return "/category/censored/";
        case 3005: return "/category/uncensored/";
        case 3006: return "/category/chinese-av/";
        case 3007: return "/category/uncensored-leaked/";
        case 3008: return "/category/sex8/";
        case 3009: return "/category/hongkongdoll/";
        case 3010: return "/label/groups/";
        default: return "/";
    }
}

static const char* javday_category_name(int channel_id) {
    switch (channel_id) {
        case 3001: return "最近更新";
        case 3002: return "人气系列";
        case 3003: return "新作上市";
        case 3004: return "有码";
        case 3005: return "无码";
        case 3006: return "国产AV";
        case 3007: return "无码流出";
        case 3008: return "杏吧";
        case 3009: return "HongKongDoll";
        case 3010: return "国产AV厂商";
        default: return "热门";
    }
}

static bool javday_fetch_category_native(const ProxyConfig& proxy,
                                         int channel_id,
                                         std::vector<AnimeItem>& out,
                                         std::string& status) {
    std::string html;
    long code = 0;
    const char* path = javday_category_path(channel_id);
    if (!javday_http_get(proxy, std::string(JAVDAY_BASE) + path, html, code, status)) return false;
    javday_parse_items(html, out, 200);
    if (out.empty()) {
        status = code == 403
            ? "JAVDAY 被站点验证拦截"
            : std::string("JAVDAY ") + javday_category_name(channel_id) + " 未解析到影片";
        return false;
    }
    status = std::string("JAVDAY ") + javday_category_name(channel_id) +
             " · " + std::to_string(out.size()) + " 条";
    return true;
}

static bool javday_fetch_home_native(const ProxyConfig& proxy,
                                     std::vector<AnimeItem>& out,
                                     std::string& status) {
    return javday_fetch_category_native(proxy, 3000, out, status);
}
'''
s = must_replace(s, old, new, "JAVDAY category fetcher")

old = r'''    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        (void)channel_id; (void)genre; (void)quarter; (void)year;
        (void)language; (void)sort_by;
        return javday_fetch_home_native(proxy, out, status);
    }'''
new = r'''    if (g_source_mode == PROVIDER_SOURCE_JAVDAY) {
        (void)genre; (void)quarter; (void)year; (void)language; (void)sort_by;
        return javday_fetch_category_native(proxy, channel_id, out, status);
    }'''
s = must_replace(s, old, new, "JAVDAY provider_filter")

p.write_text(s)

# ---------------------------------------------------------------------------
# media_resolver.cpp: treat JAVDAY HLS like movie streaming, probe before play.
# ---------------------------------------------------------------------------
p = root / "nxanime_source/media_resolver.cpp"
s = p.read_text()

old = '    const bool kanju_movie = episode.url.rfind("kanju://play/", 0) == 0;\n'
new = '''    const bool kanju_movie = episode.url.rfind("kanju://play/", 0) == 0;
    const bool javday_movie = episode.url.rfind("javday://play/", 0) == 0;
    const bool special_movie = kanju_movie || javday_movie;
'''
s = must_replace(s, old, new, "special movie detection")

s = must_replace(
    s,
    '    const int special_attempts = kanju_movie ? 5 : 1;\n',
    '    const int special_attempts = kanju_movie ? 5 : (javday_movie ? 2 : 1);\n',
    "special attempts")

s = must_replace(
    s,
    '        const std::vector<std::string>* reject_arg = kanju_movie ? &local_rejected : rejected;\n',
    '        const std::vector<std::string>* reject_arg = special_movie ? &local_rejected : rejected;\n',
    "special reject list")

s = must_replace(s, '            if (kanju_movie) {\n', '            if (special_movie) {\n', "special media probe", 1)
s = must_replace(s, '            out.movie = kanju_movie;\n', '            out.movie = special_movie;\n', "special movie flag")
s = must_replace(
    s,
    '            if (!kanju_movie) return false;\n',
    '            if (!special_movie) return false;\n',
    "handled special movie")
s = must_replace(s, '    if (kanju_movie) {\n', '    if (special_movie) {\n', "special final failure", 1)

p.write_text(s)

# ---------------------------------------------------------------------------
# cover.cpp: JAVDAY posters need their own Referer and a normal browser UA.
# ---------------------------------------------------------------------------
p = root / "nxanime_source/cover.cpp"
s = p.read_text()

old = r'''    const bool online_movie_cover = url.find("gimg0.baidu.com/") != std::string::npos ||
                                    url.find("baipiaozhe.com/") != std::string::npos;
    std::string request_url = url;'''
new = r'''    const bool online_movie_cover = url.find("gimg0.baidu.com/") != std::string::npos ||
                                    url.find("baipiaozhe.com/") != std::string::npos;
    const bool javday_cover = url.find("javday.app/") != std::string::npos ||
                             url.find("javday.homes/") != std::string::npos;
    std::string request_url = url;'''
s = must_replace(s, old, new, "JAVDAY cover classification")

old = r'''    curl_easy_setopt(curl, CURLOPT_REFERER, rrtv_cover
        ? "https://mh.yichengwlkj.com/"
        : (online_movie_cover ? "https://kanju1.com/" : "https://ani.girigirilove.com/"));
    curl_easy_setopt(curl, CURLOPT_USERAGENT,
                     "Mozilla/5.0 (Nintendo Switch; ANIMEX/0.8.3) AppleWebKit/537.36");'''
new = r'''    curl_easy_setopt(curl, CURLOPT_REFERER, rrtv_cover
        ? "https://mh.yichengwlkj.com/"
        : (online_movie_cover ? "https://kanju1.com/"
           : (javday_cover ? "https://javday.app/" : "https://ani.girigirilove.com/")));
    curl_easy_setopt(curl, CURLOPT_USERAGENT, javday_cover
        ? "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        : "Mozilla/5.0 (Nintendo Switch; ANIMEX/0.8.3) AppleWebKit/537.36");'''
s = must_replace(s, old, new, "JAVDAY cover headers")

p.write_text(s)

# ---------------------------------------------------------------------------
# main.cpp: dedicated JAVDAY tabs/categories + PIN gate before connecting.
# ---------------------------------------------------------------------------
p = root / "nxanime_source/main.cpp"
s = p.read_text()

keyboard_line = r'''static bool keyboard(const char* h,const char* g,const std::string& initial,std::string& out){SwkbdConfig k{};if(R_FAILED(swkbdCreate(&k,0)))return false;swkbdConfigMakePresetDefault(&k);swkbdConfigSetType(&k,SwkbdType_ZhHans);swkbdConfigSetHeaderText(&k,h);swkbdConfigSetGuideText(&k,g);swkbdConfigSetInitialText(&k,initial.c_str());char b[768]={0};Result rc=swkbdShow(&k,b,sizeof(b));swkbdClose(&k);if(R_FAILED(rc))return false;out=b;return true;}
'''
pin_helper = r'''
static bool javday_pin_prompt(State& st){
    SwkbdConfig k{};
    if(R_FAILED(swkbdCreate(&k,0))){st.status="JAVDAY PIN 键盘启动失败";return false;}
    swkbdConfigMakePresetPassword(&k);
    swkbdConfigSetHeaderText(&k,"JAVDAY PIN");
    swkbdConfigSetGuideText(&k,"请输入开发者 PIN");
    swkbdConfigSetStringLenMin(&k,3);
    swkbdConfigSetStringLenMax(&k,3);
    swkbdConfigSetOkButtonText(&k,"解锁");
    char b[32]={0};
    Result rc=swkbdShow(&k,b,sizeof(b));
    swkbdClose(&k);
    if(R_FAILED(rc)){st.status="已取消打开 JAVDAY";return false;}
    if(std::string(b)!="SEX"){st.status="JAVDAY PIN 错误";return false;}
    st.status="JAVDAY PIN 验证成功";
    return true;
}
'''
if pin_helper not in s:
    s = must_replace(s, keyboard_line, keyboard_line + pin_helper, "PIN helper")

anchor = r'''static const char* MOVIE_FILTER_CHANNELS[] = {"全部","电影","剧集","动漫","综艺","短剧"};
static const int MOVIE_FILTER_CHANNEL_IDS[] = {2000,2001,2010,2011,2012,2013};
'''
javday_arrays = r'''static const char* JAVDAY_FILTER_CHANNELS[] = {
    "热门","最近更新","人气系列","新作上市","有码","无码",
    "国产AV","无码流出","杏吧","HongKongDoll","国产AV厂商"
};
static const int JAVDAY_FILTER_CHANNEL_IDS[] = {
    3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010
};
static const char* JAVDAY_FILTER_ROW_NAMES[] = {"分类","类型","地区","年份","语言","排序"};
'''
if javday_arrays not in s:
    s = must_replace(s, anchor, anchor + javday_arrays, "JAVDAY filter arrays")

s = must_replace(
    s,
    'static bool online_video_data_mode(){const int mode=provider_source_mode();return mode==PROVIDER_SOURCE_RRTV||mode==PROVIDER_SOURCE_KANJU;}\n',
    '''static bool javday_data_mode(){return provider_source_mode()==PROVIDER_SOURCE_JAVDAY;}
static bool online_video_data_mode(){const int mode=provider_source_mode();return mode==PROVIDER_SOURCE_RRTV||mode==PROVIDER_SOURCE_KANJU||mode==PROVIDER_SOURCE_JAVDAY;}
''',
    "JAVDAY video data mode")

old = r'''static int filter_count(int row){
    const bool video=online_video_data_mode();
    switch(row){'''
new = r'''static int filter_count(int row){
    if(javday_data_mode())
        return row==0?(int)(sizeof(JAVDAY_FILTER_CHANNELS)/sizeof(JAVDAY_FILTER_CHANNELS[0])):1;
    const bool video=online_video_data_mode();
    switch(row){'''
s = must_replace(s, old, new, "JAVDAY filter count")

s = must_replace(
    s,
    'static const char* filter_row_name(int row){return online_video_data_mode()?VIDEO_FILTER_ROW_NAMES[row]:ANIME_FILTER_ROW_NAMES[row];}\n',
    'static const char* filter_row_name(int row){return javday_data_mode()?JAVDAY_FILTER_ROW_NAMES[row]:(online_video_data_mode()?VIDEO_FILTER_ROW_NAMES[row]:ANIME_FILTER_ROW_NAMES[row]);}\n',
    "JAVDAY filter row name")

old = r'''static const char* filter_value_text(const State& st,int row){
    const bool video=online_video_data_mode();
    switch(row){'''
new = r'''static const char* filter_value_text(const State& st,int row){
    if(javday_data_mode()) return row==0?JAVDAY_FILTER_CHANNELS[st.f_channel]:"全部";
    const bool video=online_video_data_mode();
    switch(row){'''
s = must_replace(s, old, new, "JAVDAY filter value")

s = must_replace(
    s,
    'static int filter_channel_id(const State& st){return provider_source_mode()==PROVIDER_SOURCE_KANJU?MOVIE_FILTER_CHANNEL_IDS[st.f_channel]:(online_video_data_mode()?VIDEO_FILTER_CHANNEL_IDS[st.f_channel]:ANIME_FILTER_CHANNEL_IDS[st.f_channel]);}\n',
    'static int filter_channel_id(const State& st){return provider_source_mode()==PROVIDER_SOURCE_JAVDAY?JAVDAY_FILTER_CHANNEL_IDS[st.f_channel]:(provider_source_mode()==PROVIDER_SOURCE_KANJU?MOVIE_FILTER_CHANNEL_IDS[st.f_channel]:(online_video_data_mode()?VIDEO_FILTER_CHANNEL_IDS[st.f_channel]:ANIME_FILTER_CHANNEL_IDS[st.f_channel]));}\n',
    "JAVDAY filter channel id")

s = must_replace(
    s,
    'static const char* filter_genre_value(const State& st){return st.f_genre?(online_video_data_mode()?VIDEO_FILTER_GENRES[st.f_genre]:ANIME_FILTER_GENRES[st.f_genre]):"";}\n',
    'static const char* filter_genre_value(const State& st){if(javday_data_mode())return "";return st.f_genre?(online_video_data_mode()?VIDEO_FILTER_GENRES[st.f_genre]:ANIME_FILTER_GENRES[st.f_genre]):"";}\n',
    "JAVDAY genre filter")
s = must_replace(
    s,
    'static const char* filter_region_value(const State& st){return st.f_quarter?(online_video_data_mode()?VIDEO_FILTER_REGIONS[st.f_quarter]:ANIME_FILTER_QUARTERS[st.f_quarter]):"";}\n',
    'static const char* filter_region_value(const State& st){if(javday_data_mode())return "";return st.f_quarter?(online_video_data_mode()?VIDEO_FILTER_REGIONS[st.f_quarter]:ANIME_FILTER_QUARTERS[st.f_quarter]):"";}\n',
    "JAVDAY region filter")
s = must_replace(
    s,
    'static const char* filter_language_value(const State& st){return st.f_lang?(online_video_data_mode()?VIDEO_FILTER_LANGS[st.f_lang]:ANIME_FILTER_LANGS[st.f_lang]):"";}\n',
    'static const char* filter_language_value(const State& st){if(javday_data_mode())return "";return st.f_lang?(online_video_data_mode()?VIDEO_FILTER_LANGS[st.f_lang]:ANIME_FILTER_LANGS[st.f_lang]):"";}\n',
    "JAVDAY language filter")

old = r'''static const char* VIDEO_HOME_TAB_NAMES[] = {
    "精选", "电影", "美剧", "韩剧", "日剧", "英剧", "最新", "高分", "记录", "收藏",
};
static constexpr int HOME_TAB_COUNT=10;
static const char* home_tab_name(int tab){return online_video_data_mode()?VIDEO_HOME_TAB_NAMES[tab]:ANIME_HOME_TAB_NAMES[tab];}
'''
new = r'''static const char* VIDEO_HOME_TAB_NAMES[] = {
    "精选", "电影", "美剧", "韩剧", "日剧", "英剧", "最新", "高分", "记录", "收藏",
};
static const char* JAVDAY_HOME_TAB_NAMES[] = {
    "热门", "最近", "人气", "新作", "有码", "无码", "国产", "流出", "记录", "收藏",
};
static constexpr int HOME_TAB_COUNT=10;
static const char* home_tab_name(int tab){return javday_data_mode()?JAVDAY_HOME_TAB_NAMES[tab]:(online_video_data_mode()?VIDEO_HOME_TAB_NAMES[tab]:ANIME_HOME_TAB_NAMES[tab]);}
'''
s = must_replace(s, old, new, "JAVDAY home tab names")

old = r'''static bool fetch_home_tab_data(const ProxyConfig& proxy,int tab,
                                std::vector<AnimeItem>& out,std::string& msg){
    if(online_video_data_mode()){'''
new = r'''static bool fetch_home_tab_data(const ProxyConfig& proxy,int tab,
                                std::vector<AnimeItem>& out,std::string& msg){
    if(javday_data_mode()){
        static const int ids[8]={3000,3001,3002,3003,3004,3005,3006,3007};
        return provider_filter(proxy,ids[std::max(0,std::min(tab,7))],"","","","","time",out,msg);
    }
    if(online_video_data_mode()){'''
s = must_replace(s, old, new, "JAVDAY home tab routing")

# Reset all filter indexes when switching source so channel arrays cannot go OOB.
old = r'''    st.items.clear();st.view.clear();st.media_cache.clear();st.cover.clear();st.cover_id.clear();st.home_tab=0;
    st.search.clear();st.search_next_page=ProviderSearchPage{};'''
new = r'''    st.items.clear();st.view.clear();st.media_cache.clear();st.cover.clear();st.cover_id.clear();st.home_tab=0;
    st.f_channel=0;st.f_genre=0;st.f_quarter=0;st.f_year=0;st.f_lang=0;st.f_sort=0;st.filter_row=0;
    st.search.clear();st.search_next_page=ProviderSearchPage{};'''
s = must_replace(s, old, new, "source switch filter reset")

old = '        if(hit_box(tx,ty,42,456,1196,154)){st.status="正在连接 "+provider_source_name()+"...";draw_frame(fb,st);connect_source(st,fb);}\n'
new = '''        if(hit_box(tx,ty,42,456,1196,154)){
            if(provider_source_mode()==PROVIDER_SOURCE_JAVDAY&&!javday_pin_prompt(st))return;
            st.status="正在连接 "+provider_source_name()+"...";draw_frame(fb,st);connect_source(st,fb);
        }
'''
s = must_replace(s, old, new, "touch PIN gate")

old = '                if(d&HidNpadButton_A){st.status="正在连接 "+provider_source_name()+"...";draw_frame(fb,st);connect_source(st,fb);}\n'
new = '''                if(d&HidNpadButton_A){
                    if(provider_source_mode()!=PROVIDER_SOURCE_JAVDAY||javday_pin_prompt(st)){
                        st.status="正在连接 "+provider_source_name()+"...";draw_frame(fb,st);connect_source(st,fb);
                    }
                }
'''
s = must_replace(s, old, new, "button PIN gate")

p.write_text(s)
