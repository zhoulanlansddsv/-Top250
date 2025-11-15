
from flask import Flask, request, render_template, session, redirect, url_for, flash
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from  utils.gethomeData import *
from  utils.getSearchData import *
from  utils.getTime_tData import *
from  utils.getRate_Data import *
from  utils.getmapData import *
import re
app = Flask(__name__)
app.secret_key = 'This is session_key you know ?'

# 数据库配置 - 统一使用 dbm 数据库
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '你的密码',
    'database': 'douban_plat',  # 统一使用 dbm 数据库
    'charset': 'utf8mb4'
}


# 初始化数据库连接
def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


# 创建user表（如果不存在）
def create_user_table():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 创建user表
            create_table_query = """
            CREATE TABLE IF NOT EXISTS user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(200) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_query)
        connection.commit()
        print("user表已创建或已存在于 dbm 数据库")
    except Exception as e:
        print(f"创建表时出错: {e}")
    finally:
        if connection:
            connection.close()


# 应用启动时创建表
create_user_table()

# 确保静态文件配置
app.static_folder = 'static'
app.static_url_path = '/static'


@app.route('/')
def index():
    # 检查用户是否已登录
    if 'user_id' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('login.html')
    elif request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                # 查找用户
                sql = "SELECT * FROM user WHERE email = %s"
                cursor.execute(sql, (email,))
                user = cursor.fetchone()

                if user and (user[4]==password):  # user[4]是password字段
                    # 登录成功，设置session
                    session['user_id'] = user[0]  # user[0]是id字段
                    session['user_email'] = user[3]  # user[3]是email字段
                    session['user_name'] = f"{user[1]} {user[2]}"  # user[1]是first_name, user[2]是last_name
                    return redirect(url_for('index'))
                else:
                    flash('Invalid email or password', 'error')
                    return render_template('login.html')
        except Exception as e:
            print(f"登录时出错: {e}")
            flash('Login failed. Please try again.', 'error')
            return render_template('login.html')
        finally:
            if connection:
                connection.close()


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template('register.html')
    elif request.method == "POST":
        # 获取表单数据
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        print(f"接收到注册信息: {first_name} {last_name}, {email}")

        # 验证密码是否匹配
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')

        # 使用统一的数据库连接方式
        connection = None
        try:
            # 使用 get_db_connection() 确保数据库一致性
            connection = get_db_connection()
            print("✅ 数据库连接成功 (dbm)")

            with connection.cursor() as cursor:
                # 检查邮箱是否已存在
                check_sql = "SELECT id FROM user WHERE email = %s"
                cursor.execute(check_sql, (email,))
                existing_user = cursor.fetchone()

                if existing_user:
                    flash('Email already exists', 'error')
                    print(f"❌ 邮箱已存在: {email}")
                    return render_template('register.html')

                # 创建新用户
                hashed_password = password
                print(f"🔐 密码哈希完成")

                insert_sql = """
                INSERT INTO user (first_name, last_name, email, password) 
                VALUES (%s, %s, %s, %s)
                """
                print(f"📝 执行SQL: {insert_sql}")
                print(f"📝 参数: ({first_name}, {last_name}, {email}, [hashed_password])")

                # 执行插入
                result = cursor.execute(insert_sql, (first_name, last_name, email, hashed_password))
                print(f"📊 SQL执行结果: {result} 行受影响")

            # 提交事务
            connection.commit()
            print("✅ 事务提交成功")

            # 验证插入
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
                new_user = cursor.fetchone()
                if new_user:
                    print(f"🎉 用户验证成功 - ID: {new_user[0]}, 姓名: {new_user[1]} {new_user[2]}, 邮箱: {new_user[3]}")
                else:
                    print("❌ 用户验证失败 - 未找到新插入的用户")

            print(f"🎉 用户 {email} 已成功注册到 dbm 数据库")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            if connection:
                connection.rollback()
                print("🔙 事务已回滚")
            print(f"❌ 注册失败: {e}")
            import traceback
            traceback.print_exc()
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html')
        finally:
            if connection:
                connection.close()
                print("🔒 数据库连接已关闭")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# 添加一个简单的路由来检查数据库中的用户
@app.route('/debug/users')
def debug_users():
    if 'user_id' not in session:
        return "请先登录"

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM user"
            cursor.execute(sql)
            users = cursor.fetchall()

        result = "<h1>数据库中的用户:</h1><ul>"
        for user in users:
            result += f"<li>ID: {user[0]} - {user[1]} {user[2]} - {user[3]}</li>"
        result += "</ul>"
        return result
    except Exception as e:
        return f"查询用户时出错: {e}"
    finally:
        if connection:
            connection.close()

@app.route('/search/<int:movieId>',methods=['Get','POST'])
def search(movieId):
    if request.method=='GET':
        resultData=getMovieDetailById(movieId)
    else:
        request.form=dict(request.form)
        reaultData=getMovieDetailBySearchWord(request.form['searchWord'])

    return render_template('search.html',resultData=resultData)

@app.route('/index', methods=['GET', 'POST'])
def home():
    email = session.get('email')
    tableData=getTableDate()
    return render_template(
        'index.html',
        email=email,
        tabledata=tableData

    )

@app.route('/time_t')
def time_t():
    email = session.get('email')
    row,columns=getYearData()
    return render_template(
        'time_t.html',
        email=email,
        row=row,
        columns=columns


    )
@app.route('/wordcloud_t')
def wordcloud_t():
    email = session.get('email')
    row,columns=getYearData()
    return render_template(
        'wordcloud_t.html',
        email=email,
        row=row,
        columns=columns


    )

@app.route('/map_t')
def map_t():
    email = session.get('email')
    row, columns = getMapData()

    # 添加调试输出
    print(f"=== 地图分析表调试信息 ===")
    print(f"国家数据长度: {len(row)}")
    print(f"数量数据长度: {len(columns)}")
    print(f"前5个国家: {row[:5] if row else '无数据'}")
    print(f"前5个数量: {columns[:5] if columns else '无数据'}")

    return render_template(
        'map_t.html',
        email=email,
        row=row,
        columns=columns
    )

@app.route('/rate/<type>', methods=['GET', 'POST'])
def rate_t(type):
    email = session.get('email')
    typeList = getAllTypes()
    # 传入 type 参数
    row, columns = getAllRateDataByType(type)
    yearMenRow,yearMeanColumns=getYearMeanData()
    # 添加调试信息
    print(f"类型: {type}")
    print(f"X轴数据 (row): {row}")
    print(f"Y轴数据 (columns): {columns}")
    print(f"数据长度 - X: {len(row)}, Y: {len(columns)}")

    return render_template(
        'rate.html',
        email=email,
        columns=columns,
        type=type,
        typeList=typeList,
        row=row,
        yearMenRow=yearMenRow,
        yearMeanColumns=yearMeanColumns
    )



if __name__ == '__main__':
    app.run(debug=True)