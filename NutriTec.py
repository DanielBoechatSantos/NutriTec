import sys
import sqlite3
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import os

# --- DEFINIÇÃO DE CAMINHO DO BANCO DE DADOS ---
# Isso garante que o DB seja lido sempre na mesma pasta do script
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'nutri_data.db')

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (nome TEXT PRIMARY KEY, idade INTEGER, peso REAL, altura REAL, tmb REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_usuario TEXT, data TEXT, 
                       tipo TEXT, item TEXT, calorias REAL, qtd_tempo REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS biblioteca 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, nome TEXT UNIQUE, cal_base REAL)''')
    
    # Inserir dados iniciais se a biblioteca estiver vazia
    cursor.execute("SELECT count(*) FROM biblioteca")
    if cursor.fetchone()[0] == 0:
        padroes = [
            ('alimento', 'Pão Francês', 135), ('alimento', 'Maçã', 60),
            ('alimento', 'Banana', 90), ('alimento', 'Arroz (escumadeira)', 150),
            ('alimento', 'Feijão (concha)', 100), ('alimento', 'Frango Grelhado (100g)', 160),
            ('alimento', 'Ovo Cozido', 70), ('alimento', 'Refrigerante (copo)', 90),
            ('exercicio', 'Caminhada (min)', 7), ('exercicio', 'Musculação (min)', 6)
        ]
        cursor.executemany("INSERT OR IGNORE INTO biblioteca (tipo, nome, cal_base) VALUES (?,?,?)", padroes)
    
    try:
        cursor.execute("SELECT qtd_tempo FROM registros LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE registros ADD COLUMN qtd_tempo REAL DEFAULT 0")
    conn.commit()
    conn.close()

class RegistroDialog(QDialog):
    def __init__(self, nome_usuario, data, tmb_usuario, parent=None):
        super().__init__(parent)
        self.nome_usuario, self.data, self.tmb_usuario = nome_usuario, data, tmb_usuario
        self.setWindowTitle(f"Lançamentos - {data}")
        self.setMinimumSize(600, 500)
        self.biblioteca = {'alimento': {}, 'exercicio': {}}
        self.setStyleSheet("QDialog { background-color: #1e1e1e; } QLabel { color: white; }")
        self.carregar_biblioteca()
        self.initUI()
        self.carregar_registros_existentes()

    def carregar_biblioteca(self):
        # CORREÇÃO: Usando db_path em vez de apenas o nome do arquivo
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT tipo, nome, cal_base FROM biblioteca")
        for tipo, nome, cal in c.fetchall(): self.biblioteca[tipo][nome] = cal
        conn.close()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        table_style = "QTableWidget { background-color: #2b2b2b; color: white; gridline-color: #3d3d3d; } QHeaderView::section { background-color: #3d3d3d; color: white; }"

        # ABA ALIMENTAÇÃO
        self.tab_al = QWidget(); l_al = QVBoxLayout(self.tab_al)
        box_al = QHBoxLayout(); self.cb_al = QComboBox(); self.sp_al = QDoubleSpinBox()
        self.sp_al.setRange(0.1, 999); btn_al = QPushButton("ADICIONAR")
        btn_al.clicked.connect(lambda: self.add('alimento'))
        box_al.addWidget(self.cb_al, 2); box_al.addWidget(self.sp_al); box_al.addWidget(btn_al)
        self.table_al = QTableWidget(0, 3); self.table_al.setHorizontalHeaderLabels(["Item", "Kcal", ""])
        self.table_al.setStyleSheet(table_style); self.table_al.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        l_al.addLayout(box_al); l_al.addWidget(self.table_al)
        
        # ABA EXERCÍCIO
        self.tab_ex = QWidget(); l_ex = QVBoxLayout(self.tab_ex)
        box_ex = QHBoxLayout(); self.cb_ex = QComboBox(); self.sp_ex = QDoubleSpinBox()
        self.sp_ex.setRange(1, 480); btn_ex = QPushButton("ADICIONAR")
        btn_ex.clicked.connect(lambda: self.add('exercicio'))
        box_ex.addWidget(self.cb_ex, 2); box_ex.addWidget(self.sp_ex); box_ex.addWidget(btn_ex)
        self.table_ex = QTableWidget(0, 3); self.table_ex.setHorizontalHeaderLabels(["Exercício", "Kcal", ""])
        self.table_ex.setStyleSheet(table_style); self.table_ex.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        l_ex.addLayout(box_ex); l_ex.addWidget(self.table_ex)

        self.cb_al.addItems(sorted(self.biblioteca.get('alimento', {}).keys())); self.cb_al.addItem("+ NOVO")
        self.cb_ex.addItems(sorted(self.biblioteca.get('exercicio', {}).keys())); self.cb_ex.addItem("+ NOVO")
        self.tabs.addTab(self.tab_al, "Alimentação"); self.tabs.addTab(self.tab_ex, "Exercícios")
        layout.addWidget(self.tabs)
        self.lbl_res = QLabel(""); layout.addWidget(self.lbl_res)

    def add(self, tipo):
        combo = self.cb_al if tipo == 'alimento' else self.cb_ex
        nome = combo.currentText()
        if "+" in nome:
            n, ok = QInputDialog.getText(self, "Novo", "Nome:"); c, ok2 = QInputDialog.getDouble(self, "Cal", "Kcal base:")
            if ok and ok2:
                conn = sqlite3.connect(db_path); cur = conn.cursor()
                cur.execute("INSERT OR IGNORE INTO biblioteca (tipo, nome, cal_base) VALUES (?,?,?)", (tipo, n, c))
                conn.commit(); conn.close(); self.carregar_biblioteca()
                self.cb_al.clear(); self.cb_ex.clear()
                self.cb_al.addItems(sorted(self.biblioteca['alimento'].keys())); self.cb_al.addItem("+ NOVO")
                self.cb_ex.addItems(sorted(self.biblioteca['exercicio'].keys())); self.cb_ex.addItem("+ NOVO")
            return
        qtd = self.sp_al.value() if tipo == 'alimento' else self.sp_ex.value()
        cal = self.biblioteca[tipo][nome] * qtd
        conn = sqlite3.connect(db_path); cur = conn.cursor()
        cur.execute("INSERT INTO registros (nome_usuario, data, tipo, item, calorias, qtd_tempo) VALUES (?,?,?,?,?,?)",
                  (self.nome_usuario, self.data, 'ganho' if tipo == 'alimento' else 'perda', nome, cal, qtd))
        conn.commit(); conn.close(); self.carregar_registros_existentes()

    def carregar_registros_existentes(self):
        self.table_al.setRowCount(0); self.table_ex.setRowCount(0)
        conn = sqlite3.connect(db_path); cur = conn.cursor()
        cur.execute("SELECT id, item, calorias, tipo FROM registros WHERE nome_usuario=? AND data=?", (self.nome_usuario, self.data))
        g, p = 0, 0
        for rid, item, cal, tipo in cur.fetchall():
            table = self.table_al if tipo == 'ganho' else self.table_ex
            row = table.rowCount(); table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(item))
            table.setItem(row, 1, QTableWidgetItem(f"{cal:.0f}"))
            btn_del = QPushButton("🗑️")
            btn_del.setStyleSheet("background-color: #b71c1c; color: white; font-size: 14px;")
            btn_del.clicked.connect(lambda checked, r=rid: self.del_item(r))
            table.setCellWidget(row, 2, btn_del)
            if tipo == 'ganho': g += cal
            else: p += cal
        conn.close()
        saldo = (self.tmb_usuario + p) - g
        cor = "#4caf50" if saldo >= 0 else "#f44336"
        self.lbl_res.setText(f"<b style='color:{cor}; font-size:16px;'>Saldo do dia: {saldo:.0f} kcal</b>")

    def del_item(self, rid):
        conn = sqlite3.connect(db_path); cur = conn.cursor()
        cur.execute("DELETE FROM registros WHERE id=?", (rid,)); conn.commit(); conn.close()
        self.carregar_registros_existentes()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kcalc Pro v3.0")
        self.setMinimumSize(1100, 750)
        self.usuario_atual = None
        init_db()
        self.initUI()

    def initUI(self):
        self.setStyleSheet("QMainWindow { background-color: #121212; } QLabel { color: #e0e0e0; font-family: 'Segoe UI'; } QLineEdit { background-color: #2b2b2b; color: white; border: 1px solid #3d3d3d; padding: 10px; } QPushButton { background-color: #0d47a1; color: white; font-weight: bold; padding: 8px; border-radius: 4px; }")
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        sidebar = QVBoxLayout()
        sidebar.addWidget(QLabel("<h2 style='color:#2196f3'>Kcalc</h2>"))
        self.in_nome = QLineEdit(); self.in_nome.setPlaceholderText("Nome e Enter"); self.in_nome.returnPressed.connect(self.login)
        sidebar.addWidget(self.in_nome)
        self.lbl_info = QLabel("Faça o login")
        self.lbl_ganhas = QLabel("Ingeridas: 0")
        self.lbl_perdidas = QLabel("Gastas: 0")
        self.lbl_total = QLabel("Saldo Geral: 0")
        self.lbl_peso = QLabel("Perda: 0.00 kg")
        self.lbl_proj = QLabel("\nProjeção 30 dias:")
        self.lbl_proj.setStyleSheet("color: #bb86fc; font-style: italic;")
        for w in [self.lbl_info, self.lbl_ganhas, self.lbl_perdidas, self.lbl_total, self.lbl_peso, self.lbl_proj]:
            sidebar.addWidget(w)
        self.btn_limpar = QPushButton("LIMPAR TUDO"); self.btn_limpar.setStyleSheet("background-color: #b71c1c;"); self.btn_limpar.clicked.connect(self.limpar); self.btn_limpar.hide()
        sidebar.addWidget(self.btn_limpar); sidebar.addStretch()
        self.cal = QCalendarWidget(); self.cal.clicked.connect(self.abrir_dia)
        layout.addLayout(sidebar, 1); layout.addWidget(self.cal, 3)

    def login(self):
        n = self.in_nome.text().strip()
        if not n: return
        # CORREÇÃO: Usando db_path
        conn = sqlite3.connect(db_path); cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE nome=?", (n,))
        u = cur.fetchone()
        if not u:
            i, _ = QInputDialog.getInt(self, "Novo", "Idade:", 35); p, _ = QInputDialog.getDouble(self, "Novo", "Peso:", 120); a, _ = QInputDialog.getDouble(self, "Novo", "Altura:", 170)
            t = (10 * p) + (6.25 * a) - (5 * i) + 5
            cur.execute("INSERT INTO usuarios VALUES (?,?,?,?,?)", (n, i, p, a, t)); conn.commit(); u = (n, i, p, a, t)
        self.usuario_atual, self.tmb_atual = n, u[4]
        self.lbl_info.setText(f"👤 {n}\n🔥 Basal: {self.tmb_atual:.0f} kcal"); self.btn_limpar.show(); conn.close()
        self.atualizar_visual()

    def abrir_dia(self, qdate):
        if not self.usuario_atual: return
        dialog = RegistroDialog(self.usuario_atual, qdate.toString("yyyy-MM-dd"), self.tmb_atual, self)
        dialog.exec_(); self.atualizar_visual()

    def atualizar_visual(self):
        if not self.usuario_atual: return
        conn = sqlite3.connect(db_path); cur = conn.cursor()
        cur.execute("SELECT data, tipo, SUM(calorias) FROM registros WHERE nome_usuario=? GROUP BY data, tipo", (self.usuario_atual,))
        dados, tg, tp = {}, 0, 0
        for d, t, c in cur.fetchall():
            if d not in dados: dados[d] = {'g': 0, 'p': 0}
            if t == 'ganho': dados[d]['g'] = c; tg += c
            else: dados[d]['p'] = c; tp += c
        self.cal.setDateTextFormat(QDate(), QTextCharFormat())
        for ds, v in dados.items():
            qd = QDate.fromString(ds, "yyyy-MM-dd")
            fmt = QTextCharFormat()
            if (self.tmb_atual + v['p']) >= v['g']: fmt.setBackground(QColor("#2e7d32"))
            else: fmt.setBackground(QColor("#c62828"))
            fmt.setForeground(QColor("white")); self.cal.setDateTextFormat(qd, fmt)
        cur.execute("SELECT COUNT(DISTINCT data) FROM registros WHERE nome_usuario=?", (self.usuario_atual,))
        dias = cur.fetchone()[0] or 1
        basal_acc = self.tmb_atual * dias
        saldo = (basal_acc + tp) - tg
        perda_kg = saldo/7700
        self.lbl_ganhas.setText(f"Ingeridas: {tg:.0f} kcal")
        self.lbl_perdidas.setText(f"Gastas: {(tp + basal_acc):.0f} kcal")
        self.lbl_total.setText(f"Saldo Geral: {saldo:.0f} kcal")
        self.lbl_peso.setText(f"Perda Estimada: {max(0, perda_kg):.2f} kg")
        kg_dia = perda_kg / dias
        self.lbl_proj.setText(f"\nProjeção 30 dias:\nMais {max(0, kg_dia*30):.2f} kg perdidos")
        conn.close()

    def limpar(self):
        conn = sqlite3.connect(db_path); cur = conn.cursor()
        cur.execute("DELETE FROM registros WHERE nome_usuario=?", (self.usuario_atual,))
        conn.commit(); conn.close(); self.atualizar_visual()

if __name__ == "__main__":
    app = QApplication(sys.argv); init_db()
    w = MainWindow(); w.show(); sys.exit(app.exec_())