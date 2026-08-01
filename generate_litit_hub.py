import os
import re
import json
import subprocess
from datetime import datetime, timezone, timedelta

# ================= 配置区 =================
SUMMARY_DIR = "Summary"      # 网页简报存放的目录
INDEX_OUTPUT = "index.html"  # 日历枢纽生成位置（建议仓库根目录）
tz_utc_8 = timezone(timedelta(hours=8))
AUTO_PUSH_GITHUB = True      # 生成后是否自动调用 git commit & push
# ==========================================

def scan_summary_notes():
    """扫描 Summary/ 目录下的所有 HTML 简报文件，构建日历索引数据"""
    archive_data = {}
    total_count = 0

    if not os.path.exists(SUMMARY_DIR):
        print(f"⚠️ 找不到 '{SUMMARY_DIR}' 目录，请确认目录路径！")
        return archive_data, 0

    # 递归遍历 Summary/YYYY/MM/ 文件
    for year_dir in sorted(os.listdir(SUMMARY_DIR)):
        year_path = os.path.join(SUMMARY_DIR, year_dir)
        if not os.path.isdir(year_path) or not year_dir.isdigit():
            continue

        for month_dir in sorted(os.listdir(year_path)):
            month_path = os.path.join(year_path, month_dir)
            if not os.path.isdir(month_path) or not month_dir.isdigit():
                continue

            files = sorted([f for f in os.listdir(month_path) if f.endswith('.html')], reverse=True)
            for file_name in files:
                file_full_path = os.path.join(month_path, file_name)
                rel_path = f"{SUMMARY_DIR}/{year_dir}/{month_dir}/{file_name}"

                # 尝试解析 文件名格式: safeTitle_timestamp.html
                match = re.search(r"^(.*)_(\d{10,13})\.html$", file_name)
                if match:
                    raw_title = match.group(1)
                    ts_ms = int(match.group(2))
                    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=tz_utc_8)
                else:
                    # 降级：使用文件系统的修改时间
                    raw_title = file_name.replace(".html", "")
                    mtime = os.path.getmtime(file_full_path)
                    dt = datetime.fromtimestamp(mtime, tz=tz_utc_8)

                f_year = str(dt.year)
                f_month = str(dt.month)
                f_day = str(dt.day)
                time_str = dt.strftime("%H:%M")

                display_title = f"📄 {time_str} {raw_title}"

                if f_year not in archive_data: archive_data[f_year] = {}
                if f_month not in archive_data[f_year]: archive_data[f_year][f_month] = {}
                if f_day not in archive_data[f_year][f_month]: archive_data[f_year][f_month][f_day] = []

                archive_data[f_year][f_month][f_day].append({
                    "time": time_str,
                    "path": rel_path,
                    "title": display_title,
                    "rawTitle": raw_title
                })
                total_count += 1

    return archive_data, total_count

def generate_hub_html(archive_data):
    """生成高级杂志风格的日历 WebApp (index.html)"""
    json_data = json.dumps(archive_data, ensure_ascii=False)

    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>My Litit - 网页精读日历枢纽</title>
    <style>
        :root {
            --primary: #667eea;
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #2d3748;
            --muted: #718096;
            --border: #e2e8f0;
        }
        body, html {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: var(--bg); margin: 0; padding: 0; color: var(--text); -webkit-font-smoothing: antialiased;
        }
        .container { max-width: 640px; margin: 0 auto; padding-bottom: 30px; }

        /* 顶部导航与搜索框 */
        .top-bar {
            background: var(--card); padding: 14px 18px; display: flex; gap: 10px; align-items: center;
            border-bottom: 1px solid var(--border); sticky: top: 0; z-index: 50; box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        }
        .search-input {
            flex: 1; padding: 10px 16px; border: 1.5px solid var(--border); border-radius: 20px;
            font-size: 14px; outline: none; background: #f8fafc; transition: all 0.2s;
        }
        .search-input:focus { border-color: var(--primary); background: #fff; box-shadow: 0 0 0 3px rgba(102,126,234,0.15); }
        .settings-btn { background: none; border: none; font-size: 22px; cursor: pointer; padding: 4px; border-radius: 50%; }

        /* 控制器 */
        .controls {
            padding: 15px 20px; display: flex; justify-content: center; align-items: center; gap: 10px;
            background: var(--bg); border-bottom: 1px solid var(--border);
        }
        .control-btn {
            background: var(--primary-gradient); color: #fff; border: none; border-radius: 8px;
            padding: 8px 14px; font-size: 14px; cursor: pointer; font-weight: bold; transition: all 0.2s;
            box-shadow: 0 2px 6px rgba(102,126,234,0.3);
        }
        .control-btn:active { transform: scale(0.95); opacity: 0.9; }
        .select-box {
            padding: 6px 12px; border: 1.5px solid var(--border); border-radius: 8px;
            font-size: 15px; background: #fff; outline: none; font-weight: bold; cursor: pointer; color: var(--text);
        }

        /* 日历区域 */
        .calendar-wrapper { background: var(--card); padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
        .weekdays {
            display: grid; grid-template-columns: repeat(7, 1fr); text-align: center;
            font-weight: bold; font-size: 13px; color: var(--muted); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px dashed var(--border);
        }
        .days-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
        .day-cell {
            aspect-ratio: 1; display: flex; flex-direction: column; justify-content: center; align-items: center;
            font-size: 15px; font-weight: 600; border-radius: 12px; cursor: pointer; position: relative; transition: all 0.2s;
        }
        .day-cell.empty { visibility: hidden; }
        .day-cell.has-notes { color: var(--text); font-weight: 700; }
        .day-cell.no-notes { color: #cbd5e0; }
        .day-cell.selected { background: #ebf4ff; border: 2px solid var(--primary); color: var(--primary); font-weight: bold; }
        .day-cell.today { background: #edf2f7; color: var(--text); }
        .dot { width: 6px; height: 6px; background-color: var(--primary); border-radius: 50%; position: absolute; bottom: 6px; display: none; }
        .day-cell.has-notes .dot { display: block; }

        /* 文章列表 */
        .notes-section { padding: 0 16px; }
        .note-item-wrapper { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
        .note-item {
            flex: 1; background: var(--card); border-radius: 14px; padding: 16px; display: flex;
            justify-content: space-between; align-items: center; text-decoration: none; color: var(--text);
            box-shadow: 0 2px 8px rgba(0,0,0,0.03); border-left: 4px solid var(--primary); transition: all 0.2s; overflow: hidden;
        }
        .note-item:active { transform: scale(0.98); background: #f7fafc; }
        .note-title { font-size: 15px; color: #2d3748; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left; font-weight: bold; flex: 1; }
        .delete-btn {
            background: #e53e3e; color: white; border: none; border-radius: 10px; padding: 0 16px;
            height: 52px; font-size: 16px; cursor: pointer; display: none; transition: all 0.2s; flex-shrink: 0;
        }

        .empty-state { text-align: center; padding: 40px 20px; color: var(--muted); font-size: 14px; background: var(--card); border-radius: 14px; }
        #loadingBar { height: 3px; background: var(--primary-gradient); width: 0%; transition: width 0.3s; position: fixed; top: 0; left: 0; z-index: 100; }

        /* 设置 Modal */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; justify-content: center; align-items: center; padding: 20px; backdrop-filter: blur(4px); }
        .modal-content { background: var(--card); border-radius: 16px; padding: 22px; width: 100%; max-width: 420px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); max-height: 85vh; overflow-y: auto; }
        .modal-title { margin: 0 0 15px 0; font-size: 18px; font-weight: bold; color: #1a202c; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1.5px solid var(--border); border-radius: 8px; font-size: 14px; outline: none; background: #fff; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; border-top: 1px solid var(--border); padding-top: 12px; }
        .btn { padding: 8px 16px; border-radius: 8px; border: none; font-size: 14px; font-weight: bold; cursor: pointer; }
        .btn-cancel { background: #edf2f7; color: #4a5568; }
        .btn-save { background: var(--primary-gradient); color: #fff; }
    </style>
</head>
<body>
    <div id="loadingBar"></div>

    <div class="top-bar">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 搜索网页精读标题..." autocomplete="off">
        <button class="settings-btn" id="openSettingsBtn" title="配置中心">⚙️</button>
    </div>

    <div class="container">
        <div class="controls">
            <button class="control-btn" id="prevBtn">&lt;</button>
            <select class="select-box" id="yearSelect"></select>
            <select class="select-box" id="monthSelect">
                <option value="1">01月</option><option value="2">02月</option><option value="3">03月</option>
                <option value="4">04月</option><option value="5">05月</option><option value="6">06月</option>
                <option value="7">07月</option><option value="8">08月</option><option value="9">09月</option>
                <option value="10">10月</option><option value="11">11月</option><option value="12">12月</option>
            </select>
            <button class="control-btn" id="nextBtn">&gt;</button>
            <button class="control-btn" id="todayBtn">今天</button>
        </div>

        <div class="calendar-wrapper">
            <div class="weekdays"><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span></div>
            <div class="days-grid" id="daysGrid"></div>
        </div>

        <div class="notes-section">
            <div id="notesList"></div>
        </div>
    </div>

    <!-- 设置 Modal -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal-content">
            <h3 class="modal-title">⚙️ 核心配置中心</h3>
            <p style="font-size:12px; color:#888; margin-top:-10px; margin-bottom:15px;">设置后在精读页面中点击 🤖 AI解析 即可自动同步保存。</p>
            
            <div class="form-group">
                <label>GitHub Personal Token</label>
                <input type="password" id="cfgGhToken" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx">
            </div>
            <div class="form-group" style="display:flex; gap:10px;">
                <div style="flex:1;">
                    <label>GitHub 用户名</label>
                    <input type="text" id="cfgGhOwner" placeholder="moodHappy">
                </div>
                <div style="flex:1;">
                    <label>GitHub 仓库名</label>
                    <input type="text" id="cfgGhRepo" placeholder="dual-read-notes">
                </div>
            </div>

            <div style="border-top: 1px dashed #e2e8f0; margin: 15px 0;"></div>

            <div class="form-group">
                <label>自定义 AI Endpoint URL</label>
                <input type="text" id="cfgCustomUrl" placeholder="如: https://api.chatanywhere.tech/v1/chat/completions">
            </div>
            <div class="form-group" style="display:flex; gap:10px;">
                <div style="flex:1;">
                    <label>API Key</label>
                    <input type="password" id="cfgCustomKey" placeholder="sk-xxxxxx">
                </div>
                <div style="flex:1;">
                    <label>模型名称</label>
                    <input type="text" id="cfgCustomModel" placeholder="gpt-4.1">
                </div>
            </div>

            <div class="modal-actions">
                <button class="btn btn-cancel" id="closeSettingsBtn">取消</button>
                <button class="btn btn-save" id="saveSettingsBtn">保存本地配置</button>
            </div>
        </div>
    </div>

    <script>
        const archiveData = /*DATA_START*/REPLACEME_JSON_DATA/*DATA_END*/;
        const today = new Date();
        
        const AppState = {
            year: today.getFullYear(),
            month: today.getMonth() + 1,
            day: today.getDate(),
            deleteMode: false,
            filterText: ''
        };

        function initSelects() {
            const yearSelect = document.getElementById('yearSelect');
            yearSelect.innerHTML = '';
            const allYears = new Set(Object.keys(archiveData).map(Number));
            allYears.add(today.getFullYear());
            
            Array.from(allYears).sort((a, b) => b - a).forEach(y => { 
                const opt = document.createElement('option'); 
                opt.value = y; opt.textContent = y + ' 年'; yearSelect.appendChild(opt); 
            });
        }

        function forceRender() {
            const maxDay = new Date(AppState.year, AppState.month, 0).getDate();
            if (AppState.day > maxDay) AppState.day = maxDay;

            document.getElementById('yearSelect').value = AppState.year;
            document.getElementById('monthSelect').value = AppState.month;

            const daysGrid = document.getElementById('daysGrid');
            const notesList = document.getElementById('notesList');

            daysGrid.innerHTML = ''; notesList.innerHTML = '';

            try {
                const firstDay = new Date(AppState.year, AppState.month - 1, 1).getDay() || 7;
                for (let i = 1; i < firstDay; i++) { 
                    const emptyCell = document.createElement('div'); 
                    emptyCell.className = 'day-cell empty'; daysGrid.appendChild(emptyCell); 
                }
                
                const monthData = (archiveData[AppState.year] && archiveData[AppState.year][AppState.month]) || {};
                
                for (let day = 1; day <= maxDay; day++) {
                    const cell = document.createElement('div'); cell.className = 'day-cell'; cell.textContent = day;
                    const dot = document.createElement('div'); dot.className = 'dot'; cell.appendChild(dot);
                    
                    if (monthData[day] && monthData[day].length > 0) cell.classList.add('has-notes'); else cell.classList.add('no-notes');
                    if (AppState.year === today.getFullYear() && AppState.month === today.getMonth() + 1 && day === today.getDate()) cell.classList.add('today');
                    if (day === AppState.day) cell.classList.add('selected');
                    
                    cell.onclick = () => { AppState.day = day; forceRender(); };
                    daysGrid.appendChild(cell);
                }
            } catch (err) { console.error(err); }

            try {
                let dayData = null;
                if (archiveData[AppState.year] && archiveData[AppState.year][AppState.month] && archiveData[AppState.year][AppState.month][AppState.day]) {
                    dayData = archiveData[AppState.year][AppState.month][AppState.day];
                }
                
                if (dayData && Array.isArray(dayData) && dayData.length > 0) {
                    let filtered = dayData;
                    if (AppState.filterText) {
                        filtered = dayData.filter(item => item.title.toLowerCase().includes(AppState.filterText.toLowerCase()));
                    }

                    if (filtered.length > 0) {
                        filtered.forEach((note, index) => {
                            const wrapper = document.createElement('div'); wrapper.className = 'note-item-wrapper';
                            const a = document.createElement('a'); a.href = note.path; a.className = 'note-item';
                            a.innerHTML = `<span class="note-title">${note.title}</span>`;
                            wrapper.appendChild(a);

                            const delBtn = document.createElement('button'); delBtn.className = 'delete-btn'; delBtn.innerHTML = '🗑️';
                            if (AppState.deleteMode) delBtn.style.display = 'block';
                            
                            delBtn.onclick = async (e) => {
                                e.preventDefault();
                                if(confirm('确认删除此篇精读笔记并同步删除 GitHub 云端文件吗？')) {
                                    const pathToDelete = note.path;
                                    dayData.splice(index, 1);
                                    if (dayData.length === 0) delete archiveData[AppState.year][AppState.month][AppState.day];
                                    forceRender();
                                    await syncDeleteToGithub(pathToDelete);
                                }
                            };
                            wrapper.appendChild(delBtn); notesList.appendChild(wrapper);
                        });
                    } else {
                        notesList.innerHTML = '<div class="empty-state">未找到匹配的精读笔记 🔍</div>';
                    }
                } else {
                    notesList.innerHTML = '<div class="empty-state">当日暂无精读笔记 📖</div>';
                }
            } catch (err) { console.error(err); }
        }

        document.getElementById('yearSelect').addEventListener('change', (e) => { AppState.year = parseInt(e.target.value, 10); forceRender(); });
        document.getElementById('monthSelect').addEventListener('change', (e) => { AppState.month = parseInt(e.target.value, 10); forceRender(); });
        document.getElementById('prevBtn').addEventListener('click', () => { AppState.month--; if (AppState.month < 1) { AppState.month = 12; AppState.year--; } forceRender(); });
        document.getElementById('nextBtn').addEventListener('click', () => { AppState.month++; if (AppState.month > 12) { AppState.month = 1; AppState.year++; } forceRender(); });
        document.getElementById('todayBtn').addEventListener('click', () => { AppState.year = today.getFullYear(); AppState.month = today.getMonth() + 1; AppState.day = today.getDate(); forceRender(); });

        document.getElementById('searchInput').addEventListener('input', (e) => {
            AppState.filterText = e.target.value.trim();
            forceRender();
        });

        let lastTap = 0;
        document.querySelector('.calendar-wrapper').addEventListener('click', (e) => {
            const tapLength = new Date().getTime() - lastTap;
            if (tapLength < 500 && tapLength > 0) {
                AppState.deleteMode = !AppState.deleteMode;
                document.querySelectorAll('.delete-btn').forEach(btn => btn.style.display = AppState.deleteMode ? 'block' : 'none');
                e.preventDefault();
            }
            lastTap = new Date().getTime();
        });

        initSelects(); forceRender();

        // ⚙️ 设置面板控制
        document.getElementById('openSettingsBtn').addEventListener('click', () => {
            document.getElementById('cfgGhToken').value = localStorage.getItem('GH_TOKEN') || '';
            document.getElementById('cfgGhOwner').value = localStorage.getItem('GH_OWNER') || 'moodHappy';
            document.getElementById('cfgGhRepo').value = localStorage.getItem('GH_REPO') || 'dual-read-notes';
            document.getElementById('cfgCustomUrl').value = localStorage.getItem('CUSTOM_API_URL') || '';
            document.getElementById('cfgCustomKey').value = localStorage.getItem('CUSTOM_API_KEY') || '';
            document.getElementById('cfgCustomModel').value = localStorage.getItem('CUSTOM_MODEL') || '';
            document.getElementById('settingsModal').style.display = 'flex';
        });
        document.getElementById('closeSettingsBtn').addEventListener('click', () => { document.getElementById('settingsModal').style.display = 'none'; });
        document.getElementById('saveSettingsBtn').addEventListener('click', () => {
            localStorage.setItem('GH_TOKEN', document.getElementById('cfgGhToken').value.trim());
            localStorage.setItem('GH_OWNER', document.getElementById('cfgGhOwner').value.trim());
            localStorage.setItem('GH_REPO', document.getElementById('cfgGhRepo').value.trim());
            localStorage.setItem('CUSTOM_API_URL', document.getElementById('cfgCustomUrl').value.trim());
            localStorage.setItem('CUSTOM_API_KEY', document.getElementById('cfgCustomKey').value.trim());
            localStorage.setItem('CUSTOM_MODEL', document.getElementById('cfgCustomModel').value.trim());
            document.getElementById('settingsModal').style.display = 'none';
            alert('配置已保存在本地浏览器！');
        });

        async function syncDeleteToGithub(fileRelPath) {
            const ghToken = localStorage.getItem('GH_TOKEN');
            const ghOwner = localStorage.getItem('GH_OWNER') || 'moodHappy';
            const ghRepo = localStorage.getItem('GH_REPO') || 'dual-read-notes';
            if (!ghToken) return alert('本地已移出索引，但未配置 GitHub Token，远端文件未删除。');
            try {
                const loadingBar = document.getElementById('loadingBar'); loadingBar.style.width = '30%';
                const fileRes = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/${fileRelPath}`, { headers: { 'Authorization': `Bearer ${ghToken}` } });
                if (fileRes.ok) {
                    const fileData = await fileRes.json();
                    await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/${fileRelPath}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${ghToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ message: `Delete note: ${fileRelPath}`, sha: fileData.sha }) });
                }
                loadingBar.style.width = '70%';
                const idxRes = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/index.html`, { headers: { 'Authorization': `Bearer ${ghToken}` } });
                const idxData = await idxRes.json();
                const idxContent = decodeURIComponent(escape(atob(idxData.content.replace(/\\n/g, ''))));
                
                const dataStart = idxContent.indexOf('/*DATA_START*/') + 14;
                const dataEnd = idxContent.indexOf('/*DATA_END*/');
                const newIdxContent = idxContent.substring(0, dataStart) + JSON.stringify(archiveData) + idxContent.substring(dataEnd);
                
                loadingBar.style.width = '90%';
                await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/index.html`, { method: 'PUT', headers: { 'Authorization': `Bearer ${ghToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ message: `Update index.html after deletion`, content: btoa(unescape(encodeURIComponent(newIdxContent))), sha: idxData.sha }) });
                loadingBar.style.width = '100%'; setTimeout(() => { loadingBar.style.width = '0%'; }, 1000);
            } catch(e) { console.error(e); alert('云端同步删除失败: ' + e.message); document.getElementById('loadingBar').style.width = '0%'; }
        }
    </script>
</body>
</html>"""

    html_template = html_template.replace('REPLACEME_JSON_DATA', json_data)

    with open(INDEX_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"🚀 成功生成日历枢纽 WebApp: {INDEX_OUTPUT}")

def git_push_to_github():
    """自动提交变更并推送到 GitHub 仓库"""
    if not AUTO_PUSH_GITHUB:
        return
    print("\n⏳ 正在自动推送变更到 GitHub...")
    if not os.path.exists(".git"):
        print("⚠️ 当前目录并非 Git 仓库，跳过 Git Push。")
        return
    try:
        subprocess.run(["git", "add", "."], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            print("ℹ️ 没有发现需要推播的更新。")
            return

        subprocess.run(["git", "commit", "-m", "Auto-update Litit reading calendar index"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        print("✅ 成功同步推送到 GitHub！网页版日历约在 1 分钟后更新可见。")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git 执行失败，错误码: {e.returncode}")

def main():
    print("=======================================")
    print("📚 My Litit - 精读日历枢纽生成器")
    print("=======================================")
    archive_data, count = scan_summary_notes()
    print(f"🔍 扫描完成，共找到 {count} 篇网页精读简报。")
    generate_hub_html(archive_data)
    git_push_to_github()

if __name__ == "__main__":
    main()