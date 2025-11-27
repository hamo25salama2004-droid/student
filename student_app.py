import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="بوابة الطالب", page_icon="🎓")

# --- دالة الاتصال ---
def get_database():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ خطأ في الإعدادات: لم يتم العثور على مفتاح الخدمة.")
            st.stop()
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        return client.open("School_System")
    except Exception as e:
        st.error(f"⚠️ فشل الاتصال بقاعدة البيانات. (الخطأ: {e})")
        st.stop()

# --- تسجيل الدخول ---
if 'student_logged_in' not in st.session_state:
    st.session_state['student_logged_in'] = False

if not st.session_state['student_logged_in']:
    st.title("🔐 تسجيل دخول الطالب")
    with st.form("st_login"):
        user_code = st.text_input("كود الطالب").strip()
        user_pass = st.text_input("الباسوورد", type="password").strip()
        btn = st.form_submit_button("دخول")
        
        if btn:
            sheet = get_database()
            ws = sheet.worksheet("Students")
            
            try:
                cell = ws.find(user_code)
                if cell:
                    row_vals = ws.row_values(cell.row)
                    real_pass = row_vals[5]
                    
                    if user_pass == real_pass and real_pass != "":
                        st.session_state['student_logged_in'] = True
                        st.session_state['student_data'] = row_vals
                        st.session_state['student_id'] = user_code
                        st.rerun()
                    else:
                        st.error("بيانات خاطئة أو لم يتم دفع المصاريف لتوليد الباسوورد.")
                else:
                    st.error("الكود غير موجود")
            except Exception:
                st.error("حدث خطأ أثناء محاولة البحث.")

# --- لوحة التحكم ---
else:
    data = st.session_state['student_data']
    st_id = st.session_state['student_id']
    
    st.title(f"مرحباً بك، {data[1]} 👋")
    
    sheet = get_database()

    # 1. بيانات الطالب المالية والشخصية
    st.subheader("📄 بياناتي الأساسية")
    col1, col2, col3 = st.columns(3)
    col1.metric("كود الطالب", data[0])
    col2.metric("المبلغ المدفوع", f"{data[4]} ج.م")
    col3.metric("المصاريف المتبقية", f"{float(data[3]) - float(data[4])} ج.م")
    
    # 2. المواد والروابط (الروابط العامة)
    st.subheader("📚 المواد والروابط المتاحة")
    
    @st.cache_data(ttl=5) # تحديث البيانات كل 5 ثواني
    def load_materials():
        ws_mat = sheet.worksheet("Materials")
        return pd.DataFrame(ws_mat.get_all_records())

    mat_data = load_materials()
    
    # يتم عرض الروابط العامة والخاصة بالمعلم الذي سجلها كـ "Subject"
    global_mats = mat_data[
        (mat_data['Type'] == 'Global') | 
        (mat_data['Type'] == 'Subject') # هنا يجب أن تكون هناك فلترة على TeacherID إذا أردت تخصيصها أكثر
    ]
    
    if not global_mats.empty:
        # استخدام الأعمدة والأزرار المنسقة لتبدو أنيقة وواضحة
        cols = st.columns(3) 
        for index, row in global_mats.iterrows():
            with cols[index % 3]: 
                st.link_button(
                    label=f"🔗 {row['Title']}", 
                    url=row['Link'], 
                    help=f"النوع: {row['Type']}"
                )
    else:
        st.info("لا توجد مواد أو روابط متاحة حالياً.")

    # 3. النتائج والدرجات
    st.subheader("🏆 النتائج والدرجات")

    @st.cache_data(ttl=5) # تحديث البيانات كل 5 ثواني
    def load_grades(st_id_val):
        ws_grades = sheet.worksheet("Grades")
        df_grades = pd.DataFrame(ws_grades.get_all_records())
        return df_grades[df_grades['StudentID'].astype(str) == st_id_val]

    my_grades = load_grades(st_id)
    
    if not my_grades.empty:
        st.dataframe(my_grades[['Subject', 'Score', 'Status', 'Date']], hide_index=True)
    else:
        st.info("لم يتم رصد درجات لك بعد.")
