
import sys, traceback, csv, os, json, re
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import *
from PySide6.QtGui import QPen, QBrush, QColor, QFont
from PySide6.QtCore import Qt,QDate, QRectF
import database as db

def money(v):
    try:return f"₹{float(v):,.2f}"
    except:return "₹0.00"

def confirm_delete(parent, title, message, detail="THIS ACTION CANNOT BE UNDONE."):
    dlg=QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    dlg.setFixedSize(470,230)
    dlg.setStyleSheet("""
        QDialog{background:#15171c;color:#f5f1e8}
        QLabel{color:#f5f1e8}
        QPushButton{min-height:38px;padding:8px 22px;border-radius:7px;font-weight:600}
        QPushButton#deleteBtn{background:#8f2f2f;border:1px solid #b84b4b;color:white}
        QPushButton#cancelBtn{background:#252a32;border:1px solid #4b515c;color:white}
        QPushButton:hover{background:#343a45}
        QPushButton#deleteBtn:hover{background:#a83a3a}
    """)
    lay=QVBoxLayout(dlg)
    title_lbl=QLabel(title.upper())
    title_lbl.setStyleSheet("font-size:18px;font-weight:700;letter-spacing:1px")
    lay.addWidget(title_lbl)
    msg_lbl=QLabel(message)
    msg_lbl.setWordWrap(True)
    msg_lbl.setStyleSheet("font-size:14px;font-weight:600;margin-top:8px")
    lay.addWidget(msg_lbl)
    detail_lbl=QLabel(detail)
    detail_lbl.setStyleSheet("font-size:11px;color:#aaa")
    lay.addWidget(detail_lbl)
    lay.addStretch()
    row=QHBoxLayout()
    row.addStretch()
    cancel=QPushButton("CANCEL");cancel.setObjectName("cancelBtn");cancel.clicked.connect(dlg.reject)
    delete=QPushButton("DELETE");delete.setObjectName("deleteBtn");delete.clicked.connect(dlg.accept)
    row.addWidget(cancel);row.addWidget(delete)
    lay.addLayout(row)
    dlg.exec()
    return dlg.result()==QDialog.Accepted

class UpperLineEdit(QLineEdit):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.textChanged.connect(self._up)
    def _up(self,text):
        u=text.upper()
        if text!=u:
            pos=self.cursorPosition();self.blockSignals(True);self.setText(u);self.setCursorPosition(min(pos,len(u)));self.blockSignals(False)

class OldStockSpinBox(QDoubleSpinBox):
    def focusInEvent(self,event):
        super().focusInEvent(event)
        self.lineEdit().selectAll()

    def mousePressEvent(self,event):
        super().mousePressEvent(event)
        self.lineEdit().selectAll()

class BillDateEdit(QLineEdit):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.setPlaceholderText("DDMMYY")
        self.setMaxLength(10)
        self.setReadOnly(False)
    def mousePressEvent(self,event):
        super().mousePressEvent(event); self.setCursorPosition(0)
    def focusInEvent(self,event):
        super().focusInEvent(event); self.setCursorPosition(0)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key_Backspace,Qt.Key_Delete):
            digits=''.join(ch for ch in self.text() if ch.isdigit())
            if digits:
                digits=digits[:-1]
                shown=digits
                if len(digits)>2: shown=digits[:2]+"-"+digits[2:]
                if len(digits)>4: shown=digits[:2]+"-"+digits[2:4]+"-"+digits[4:]
                self.setText(shown)
                self.setCursorPosition(len(shown))
            return
        if event.text().isdigit():
            digits=''.join(ch for ch in self.text() if ch.isdigit())
            if len(digits)>=6:return
            digits+=event.text()
            shown=digits
            if len(digits)>2: shown=digits[:2]+"-"+digits[2:]
            if len(digits)>4: shown=digits[:2]+"-"+digits[2:4]+"-"+digits[4:]
            self.setText(shown); self.setCursorPosition(len(shown)); return
        super().keyPressEvent(event)

class PurchaseDateEdit(QLineEdit):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.setPlaceholderText("DDMMYY")
        self.setReadOnly(False)
        self.setMaxLength(8)

    def mousePressEvent(self,event):
        super().mousePressEvent(event)
        self.setCursorPosition(0)

    def focusInEvent(self,event):
        super().focusInEvent(event)
        self.setCursorPosition(0)

    def keyPressEvent(self,event):
        if event.key() in (Qt.Key_Backspace,Qt.Key_Delete):
            digits=''.join(ch for ch in self.text() if ch.isdigit())
            if digits:
                digits=digits[:-1]
                shown=digits
                if len(digits)>2: shown=digits[:2]+"-"+digits[2:]
                if len(digits)>4: shown=digits[:2]+"-"+digits[2:4]+"-"+digits[4:]
                self.setText(shown)
                self.setCursorPosition(len(shown))
            return
        text=event.text()
        if text.isdigit():
            digits=''.join(ch for ch in self.text() if ch.isdigit())
            if len(digits)>=6:
                return
            digits+=text
            shown=digits
            if len(digits)>2: shown=digits[:2]+"-"+digits[2:]
            if len(digits)>4: shown=digits[:2]+"-"+digits[2:4]+"-"+digits[4:]
            self.setText(shown)
            self.setCursorPosition(len(shown))
            return
        super().keyPressEvent(event)

    def date_value(self):
        digits=''.join(ch for ch in self.text() if ch.isdigit())
        if len(digits)!=6:
            raise ValueError("Date must be DDMMYY")
        dd,mm,yy=digits[:2],digits[2:4],digits[4:6]
        year=2000+int(yy)
        return datetime(year,int(mm),int(dd)).strftime("%Y-%m-%d")

STYLE="""QWidget{background:#111318;color:#f4f0e7;font-family:Segoe UI;font-size:13px}
QLineEdit,QComboBox,QDateEdit,QDoubleSpinBox{background:#0b0d10;color:#fff;border:1px solid #3c424d;border-radius:6px;padding:7px}
QPushButton{background:#252b34;color:#fff;border:1px solid #454b56;border-radius:7px;padding:9px 14px}
QPushButton:hover{background:#343b48} QTableWidget{background:#0b0d10;gridline-color:#292d35}
QHeaderView::section{background:#20252d;color:#fff;padding:7px} QGroupBox{border:1px solid #343943;border-radius:9px;margin-top:10px;padding:10px;font-weight:600}"""

MODULES={"parties":"PARTIES","purchase":"PURCHASE","stock":"STOCK","mrpgen":"MRP GENERATOR","barcode":"BARCODE GENERATOR","billview":"BILL VIEW","billing":"BILLING","reports":"REPORTS","customers":"CUSTOMERS","settings":"SETTINGS","users":"STAFF PERMISSIONS","oldstock":"OLD STOCK ENTRY"}

class Login(QWidget):
    def __init__(self):
        super().__init__();self.setWindowTitle("RANISAA ERP");self.setFixedSize(430,370);l=QVBoxLayout(self)
        t=QLabel("RANISAA EXCLUSIVE");t.setAlignment(Qt.AlignCenter);t.setStyleSheet("font-size:28px;font-weight:bold")
        self.u=QLineEdit();self.u.setPlaceholderText("USERNAME");self.p=QLineEdit();self.p.setPlaceholderText("PASSWORD");self.p.setEchoMode(QLineEdit.Password)
        b=QPushButton("LOGIN");b.clicked.connect(self.go);self.p.returnPressed.connect(self.go)
        for x in(t,QLabel("ERP • BUSINESS MANAGEMENT"),self.u,self.p,b):l.addWidget(x)
    def go(self):
        u=db.login(self.u.text().strip(),self.p.text())
        if not u:return QMessageBox.warning(self,"LOGIN","Invalid username/password")
        self.d=Dash(u);self.d.show();self.close()

class Dash(QWidget):
    def __init__(self,user):
        super().__init__();self.user=user;self.p=db.perms(user["role"]);self.ws=[];self.setWindowTitle("RANISAA ERP");self.resize(1200,760);l=QVBoxLayout(self)
        h=QHBoxLayout();h.addWidget(QLabel("RANISAA ERP"));h.addStretch();h.addWidget(QLabel(f"{user['full_name']} • {user['role'].upper()}"));l.addLayout(h)
        grid=QGridLayout()
        cls={"purchase":Purchase,"stock":Stock,"mrpgen":MRPBarcode,"barcode":BarcodeGenerator,"billview":BillView,"billing":Billing,"reports":Reports,"customers":Customers,"parties":Parties,"settings":Settings,"users":Permissions,"oldstock":OldStockEntry,"billview":BillView}
        visible=[]
        for k,label in MODULES.items():
            if k=="billview" and self.user["role"]!="admin": continue
            visible.append((k,label))
        for i,(k,label) in enumerate(visible):
            b=QPushButton(label);b.setMinimumHeight(65);perm_key="mrp" if k in ("mrpgen","barcode") else k;b.setEnabled(self.p.get(perm_key,False) or (k in ("billview","oldstock") and self.user["role"]=="admin"));grid.addWidget(b,i//3,i%3);b.clicked.connect(lambda _,c=cls[k]:self.open(c))
        l.addLayout(grid);logout=QPushButton("LOGOUT");logout.clicked.connect(self.logout);l.addWidget(logout);l.addStretch();l.addWidget(QLabel("DATA IS STORED SEPARATELY FROM THE APPLICATION. UNINSTALLING THE APP DOES NOT DELETE DATA/."))
    def open(self,c):
        # Bill View should never reveal another already-open module when it closes.
        if c is BillView:
            for old in self.ws:
                if old is not None and old.isVisible():
                    old.hide()
        w=c(self.user)
        if getattr(w,"_startup_cancelled",False):
            return
        w._dash=self
        w.show();self.ws.append(w)
    def logout(self):
        self.close();self.login=Login();self.login.show()

class Purchase(QWidget):
    def __init__(self,user):
        super().__init__();self.user=user;self.rows=[];self.setWindowTitle("PURCHASE");self.resize(1280,800);l=QVBoxLayout(self)
        g=QGridLayout();self.bill=UpperLineEdit();self.bill.setPlaceholderText("ENTER INVOICE NUMBER");self.dt=PurchaseDateEdit()
        self.party=QComboBox();self.party.setEditable(True);self.party.setCurrentIndex(-1);self.party.setInsertPolicy(QComboBox.NoInsert)
        self.party.setCompleter(QCompleter([x["name"] for x in db.parties()],self.party))
        self.party.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.party.completer().setFilterMode(Qt.MatchContains)
        self.party.setToolTip("Select or type the complete party name")
        self.party.lineEdit().setPlaceholderText("PARTY NAME")
        self.gstin=QLineEdit();self.gstin.setReadOnly(True)
        for lab,w,r,c in[("Invoice No.",self.bill,0,0),("Date (DDMMYYYY)",self.dt,0,2),("Party Name",self.party,1,0),("Party GST Number",self.gstin,1,2)]:g.addWidget(QLabel(lab),r,c);g.addWidget(w,r,c+1)
        l.addLayout(g);self.party.setCurrentIndex(-1);self.party.currentTextChanged.connect(self.pc)
        box=QGroupBox("ADD ITEM");gg=QGridLayout(box);self.n=UpperLineEdit();self.h=UpperLineEdit();self.pr=QLineEdit();self.gs=QComboBox();self.gs.addItems(["5%","18%"]);self.q=QLineEdit();self.d=UpperLineEdit()
        self.attr_type=QComboBox();self.attr_type.addItems(["NONE","COLOR","SIZE","BOTH"])
        self.attr_values=UpperLineEdit();self.attr_values.setPlaceholderText("BLUE, GREEN, YELLOW / L, XL, XXL")
        for i,(lab,w) in enumerate([("Item Name",self.n),("HSN Code",self.h),("Price WITHOUT GST",self.pr),("GST",self.gs),("Quantity",self.q),("Design Number",self.d),("TYPE",self.attr_type),("COLOR / SIZE",self.attr_values)]):
            gg.addWidget(QLabel(lab),0,i);gg.addWidget(w,1,i)
        a=QPushButton("ADD ITEM");a.clicked.connect(self.add);gg.addWidget(a,1,8);gg.setColumnStretch(0,2);gg.setColumnStretch(1,2);gg.setColumnStretch(2,2);gg.setColumnStretch(3,1);gg.setColumnStretch(4,1);gg.setColumnStretch(5,2);gg.setColumnStretch(6,1);gg.setColumnStretch(7,2);gg.setColumnStretch(8,1);l.addWidget(box)
        self.h.setCompleter(QCompleter(db.hsn(),self.h));self.n.setCompleter(QCompleter([x["name"] for x in db.items()],self.n))
        self.t=QTableWidget(0,11);self.t.setHorizontalHeaderLabels(["ITEM","HSN","DESIGN NUMBER","COLOR / SIZE","PRICE","GST %","QTY","TAXABLE","GST AMOUNT","TOTAL",""]);self.t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);l.addWidget(self.t)
        self.s=QLabel();self.s.setMinimumHeight(52);self.s.setWordWrap(True);l.addWidget(self.s)
        save=QPushButton("SAVE BILL")
        save.clicked.connect(self.save)
        btn=QHBoxLayout()
        btn.addStretch()
        btn.addWidget(save)
        l.addLayout(btn)
        self.calc()
    def _parse_purchase_attributes(self):
        attr_type=self.attr_type.currentText().strip().upper()
        raw=self.attr_values.text().strip()
        if attr_type=="NONE":
            return raw.upper(), "", []
        if attr_type=="COLOR":
            vals=list(dict.fromkeys(v.strip().upper() for v in re.split(r"[,/&]+",raw) if v.strip()))
            return ", ".join(vals), "", vals
        if attr_type=="SIZE":
            vals=list(dict.fromkeys(v.strip().upper() for v in re.split(r"[,]+",raw) if v.strip()))
            return "", ", ".join(vals), vals
        if attr_type=="BOTH":
            colors=[]; details=[]
            for group in [g.strip() for g in raw.split("/") if g.strip()]:
                bits=group.split(None,1)
                if len(bits)!=2:
                    raise ValueError("BOTH format: BLUE L,XL / GREEN XXL")
                color=bits[0].strip().upper()
                sz=list(dict.fromkeys(v.strip().upper() for v in bits[1].split(",") if v.strip()))
                if not sz:
                    raise ValueError("BOTH format: BLUE L,XL / GREEN XXL")
                colors.append(color)
                details.append(f"{color}: {', '.join(sz)}")
            return ", ".join(dict.fromkeys(colors)), " / ".join(details), details
        return "", "", []

    def pc(self,x):
        u=x.upper()
        if x != u:
            le=self.party.lineEdit()
            pos=le.cursorPosition()
            le.blockSignals(True);le.setText(u);le.setCursorPosition(min(pos,len(u)));le.blockSignals(False)
        p=db.party_by_name(u);self.gstin.setText(p["gstin"] if p else "")
    def add(self):
        try:
            p=float(self.pr.text() or 0);q=float(self.q.text() or 0);g=float(self.gs.currentText()[:-1])
        except:
            return QMessageBox.warning(self,"PURCHASE","ENTER VALID PRICE AND QUANTITY.")
        if not all([self.n.text().strip(),self.h.text().strip(),self.d.text().strip()]) or p<=0 or q<=0:
            return QMessageBox.warning(self,"PURCHASE","FILL ITEM NAME, HSN, PRICE, QUANTITY AND DESIGN NUMBER.")
        tx=p*q;ga=tx*g/100
        # IMPORTANT: ADD ITEM ONLY STAGES IT IN THE CURRENT BILL.
        # NOTHING IS WRITTEN TO STOCK/DATABASE UNTIL SAVE BILL.
        try:
            color,size,detail=self._parse_purchase_attributes()
        except ValueError as ex:
            return QMessageBox.warning(self,"PURCHASE",str(ex))
        self.rows.append({"id":None,"name":self.n.text().strip(),"hsn":self.h.text().strip(),
                          "design":self.d.text().strip(),"color":color,"size":size,
                          "attribute_detail":detail,"attribute_type":self.attr_type.currentText(),
                          "price":p,"qty":q,"gst":g,"tax":tx,"ga":ga})
        self.refresh()
        for w in (self.n,self.h,self.pr,self.q,self.d,self.attr_values): w.clear()
        self.attr_type.setCurrentIndex(0)

    def refresh(self):
        self.t.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            attr=" / ".join(x.get("attribute_detail") or [])
            if not attr:
                attr=x.get("color") or x.get("size") or ""
            vals=[x["name"],x["hsn"],x["design"],attr,money(x["price"]),f'{x["gst"]:.0f}%',x["qty"],money(x["tax"]),money(x["ga"]),money(x["tax"]+x["ga"])]
            for c,v in enumerate(vals): self.t.setItem(r,c,QTableWidgetItem(str(v)))
            d=QPushButton("🗑");d.setToolTip("REMOVE ITEM");d.setFixedSize(34,30)
            d.clicked.connect(lambda _,rr=r:self.delete_row(rr))
            self.t.setCellWidget(r,9,d)
        self.calc()

    def calc(self):
        taxable = sum(float(x["tax"]) for x in self.rows)
        ga = sum(float(x["ga"]) for x in self.rows)
        total = taxable + ga
        gst5 = sum(float(x["ga"]) for x in self.rows if abs(float(x["gst"])-5.0)<0.001)
        gst18 = sum(float(x["ga"]) for x in self.rows if abs(float(x["gst"])-18.0)<0.001)
        self.s.setText(
            f"TAXABLE ₹{taxable:,.2f}    |    GST 5% ₹{gst5:,.2f}    |    GST 18% ₹{gst18:,.2f}    |    TOTAL GST ₹{ga:,.2f}    |    GRAND TOTAL ₹{total:,.2f}"
        )
        self.s.setStyleSheet("font-size:13px;font-weight:700;padding:12px;background:#191d24;border:1px solid #343943;border-radius:9px")

    def delete_row(self,r):
        if 0 <= r < len(self.rows):
            item_name=self.rows[r]["name"]
            if not confirm_delete(
                self,
                "REMOVE ITEM",
                f"REMOVE “{item_name}” FROM THIS PURCHASE?",
                "THE ITEM WILL ONLY BE REMOVED FROM THE CURRENT BILL. STOCK IS NOT CHANGED."
            ):
                return
            self.rows.pop(r)
            self.refresh()

    def save(self):
        if not self.rows:
            return QMessageBox.warning(self,"PURCHASE","ADD AT LEAST ONE ITEM BEFORE SAVING.")
        invoice=self.bill.text().strip()
        party=self.party.currentText().strip()
        if not invoice:
            return QMessageBox.warning(self,"PURCHASE","ENTER INVOICE NUMBER.")
        if not party:
            return QMessageBox.warning(self,"PURCHASE","SELECT OR ENTER PARTY NAME.")
        try:
            typed_date=self.dt.date_value()
        except ValueError:
            return QMessageBox.warning(self,"PURCHASE","ENTER DATE AS DDMMYY. EXAMPLE: 101226 = 10-12-2026.")
        if db.purchase_exists(invoice,party):
            return QMessageBox.warning(self,"DUPLICATE PURCHASE",f"INVOICE {invoice} FOR {party} ALREADY EXISTS.")
        try:
            tx=sum(x["tax"] for x in self.rows);ga=sum(x["ga"] for x in self.rows)
            db.save_purchase_atomic(
                {"bill":invoice,"party":party,"gstin":self.gstin.text(),"date":typed_date,
                 "total":tx+ga,"gst":ga,"user":self.user["id"]},
                self.rows
            )
        except Exception as e:
            err=traceback.format_exc()
            db.log_error(err)
            return QMessageBox.critical(
                self,"PURCHASE",
                f"COULD NOT SAVE BILL.\n\n{type(e).__name__}: {e}\n\nNO PURCHASE/STOCK CHANGES WERE COMMITTED."
            )
        QMessageBox.information(
            self,"SAVED",
            "PURCHASE BILL SAVED SUCCESSFULLY.\\n\\nSTOCK HAS BEEN UPDATED."
        )
        self.clear_bill()
        self.bill.setFocus()

    def closeEvent(self,event):
        if self.rows:
            ans=QMessageBox.question(
                self,
                "CLOSE PURCHASE",
                "PURCHASE ENTRY IS NOT SAVED.\n\nDO YOU WANT TO CLOSE WITHOUT SAVING?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if ans != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()

    def clear_bill(self):
        self.rows=[];self.t.setRowCount(0);self.bill.clear();self.party.setCurrentIndex(-1);self.gstin.clear();self.dt.clear();self.party.setCurrentText("");self.gstin.clear();self.calc()
class MRPBarcode(QWidget):
    def __init__(self,user):
        super().__init__()
        self.user=user
        self.rows=[]
        self.setWindowTitle("MRP GENERATOR")
        self.setWindowState(Qt.WindowNoState)
        self.resize(1320,820)
        self.setMinimumSize(900,600)
        self.setStyleSheet("""
            QGroupBox{border:1px solid #343943;border-radius:10px;margin-top:10px;padding:12px;font-weight:700}
            QDoubleSpinBox{min-height:34px}
            QLineEdit{min-height:34px}
            QPushButton{min-height:38px}
        """)

        l=QVBoxLayout(self)
        title=QLabel("MRP GENERATOR")
        title.setStyleSheet("font-size:22px;font-weight:700")
        l.addWidget(title)

        box=QGroupBox("SELECT PURCHASE")
        g=QGridLayout(box)

        self.party=QComboBox()
        self.party.setMinimumWidth(300)
        self.party.setEditable(True)
        self.party.setInsertPolicy(QComboBox.NoInsert)
        self.party.addItems([x["name"] for x in db.parties()])
        self.party.setCurrentIndex(-1)
        self.party.lineEdit().setPlaceholderText("TYPE PARTY NAME")
        self.party.lineEdit().setClearButtonEnabled(True)
        self.party.setCompleter(QCompleter([x["name"] for x in db.parties()],self.party))
        self.party.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.party.completer().setFilterMode(Qt.MatchContains)
        self.party.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.party.lineEdit().textEdited.connect(lambda text: self._party_suggest(text))

        self.invoice=UpperLineEdit()
        self.invoice.setPlaceholderText("ENTER INVOICE NUMBER")

        load=QPushButton("LOAD PURCHASE")
        load.clicked.connect(self.load_purchase)

        g.addWidget(QLabel("PARTY NAME"),0,0);g.addWidget(self.party,0,1)
        g.addWidget(QLabel("INVOICE NUMBER"),0,2);g.addWidget(self.invoice,0,3)
        g.addWidget(load,0,4)
        l.addWidget(box)

        info=QLabel("MRP = PRICE WITHOUT GST × MULTIPLIER  •  USE A DIFFERENT MULTIPLIER FOR ANY INDIVIDUAL ITEM")
        info.setStyleSheet("font-size:11px;color:#9da4b0;padding:4px")
        l.addWidget(info)

        self.t=QTableWidget(0,11)
        self.t.setHorizontalHeaderLabels([
            "ITEM","STYLE / DESIGN","COLOR","SIZE","QTY","PRICE WITHOUT GST","MULTIPLIER","MRP","GST %","BARCODE",""
        ])
        self.t.horizontalHeader().setStretchLastSection(True)
        self.t.setAlternatingRowColors(True)
        self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setContextMenuPolicy(Qt.CustomContextMenu)
        self.t.customContextMenuRequested.connect(self.mrp_context_menu)
        self.t.verticalHeader().setDefaultSectionSize(42)
        self.t.setWordWrap(False)
        l.addWidget(self.t,1)

        actions=QHBoxLayout()
        self.save_all_btn=QPushButton("SAVE ALL MRP")
        self.save_all_btn.setMinimumHeight(46)
        self.save_all_btn.setMinimumWidth(170)
        self.save_all_btn.setStyleSheet("""
            QPushButton{background:#b9975b;color:#111;border:none;border-radius:8px;
                        font-size:13px;font-weight:800;padding:10px 24px}
            QPushButton:hover{background:#d0b778}
            QPushButton:pressed{background:#a8874f}
        """)
        self.save_all_btn.clicked.connect(self.save_all_mrp)
        self.save_all_btn.setEnabled(False)
        actions.addStretch()
        actions.addWidget(self.save_all_btn)

        if not hasattr(self,"print_btn"):
            self.print_btn=QPushButton("PRINT")
            self.print_btn.hide()
        if not hasattr(self,"save_all_btn"):
            self.save_all_btn=QPushButton("SAVE ALL")
            self.save_all_btn.hide()
        self.print_btn.setMinimumHeight(46)
        self.print_btn.setEnabled(False)
        actions.addWidget(self.print_btn)
        l.addLayout(actions)

        self.party.currentTextChanged.connect(self.party_changed)

    def _party_suggest(self,text):
        comp=self.party.completer()
        if len(text.strip())>=2:
            comp.setCompletionPrefix(text.strip())
            comp.complete()
        else:
            comp.popup().hide()

    def party_changed(self,n):
        self.invoice.clear()
        # Invoice is manually entered now, so party change only clears the previous invoice.
        self.rows=[]
        self.t.setRowCount(0)
        self.print_btn.setEnabled(False)

    def load_purchase(self):
        party_name=self.party.currentText().strip()
        bill=self.invoice.text().strip()
        if not party_name:
            return QMessageBox.warning(self,"MRP","SELECT PARTY NAME.")
        if not bill:
            return QMessageBox.warning(self,"MRP","ENTER INVOICE NUMBER.")

        recs=db.purchase_lookup(party_name,bill)
        if not recs:
            return QMessageBox.warning(self,"MRP","PURCHASE BILL NOT FOUND FOR THIS PARTY AND INVOICE.")
        rec=recs[0]
        pid=int(rec["id"])
        self.rows=db.purchase_items_lookup(pid)
        if not self.rows:
            return QMessageBox.warning(self,"MRP","NO ITEMS FOUND IN THIS PURCHASE.")
        party_rec=db.party_by_name(party_name) or {}
        manufacturer_code=str(party_rec.get("manufacturer_code","") or "RLT").strip().upper()
        bill_date=str(rec.get("bill_date") or "")
        for x in self.rows:
            x["_party_code"]=manufacturer_code
            x["_bill_date"]=bill_date
            x["_invoice"]=str(rec.get("bill_number") or bill)

        # Header details.
        if hasattr(self,"bill_info"):
            self.bill_info.deleteLater()
        card=QFrame()
        card.setObjectName("billInfo")
        card.setStyleSheet("QFrame#billInfo{background:#191d24;border:1px solid #303641;border-radius:10px}")
        g=QGridLayout(card);g.setHorizontalSpacing(28);g.setVerticalSpacing(8)
        raw=str(rec.get("bill_date") or "")
        try: date_display=datetime.strptime(raw,"%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError: date_display=raw
        fields=[
            ("PARTY",rec.get("supplier_name","—")),
            ("INVOICE",rec.get("bill_number","—")),
            ("PURCHASE DATE",date_display),
            ("GSTIN",rec.get("supplier_gstin","—") or "—"),
            ("BILL TOTAL",money(rec.get("total_amount",0))),
        ]
        for i,(lab,val) in enumerate(fields):
            col=i%3; row=i//3
            q=QLabel(f"{lab}\n{val}")
            q.setStyleSheet("color:#f5f1e8;font-size:12px;font-weight:600")
            q.setWordWrap(True)
            g.addWidget(q,row,col)
        self.bill_info=card
        # Put header immediately before the table.
        parent=self.t.parentWidget()
        lay=parent.layout() if parent else None
        if lay:
            idx=lay.indexOf(self.t)
            lay.insertWidget(idx,card)

        self.t.setColumnCount(11)
        self.t.setHorizontalHeaderLabels([
            "ITEM","HSN","DESIGN NUMBER","COLOR","SIZE","QTY","PURCHASE RATE","GST %",
            "MULTIPLIER","MRP","BARCODE"
        ])
        self.t.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            price=float(x["rate"] or 0); gst=float(x["gst_rate"] or 0)
            qty=float(x["quantity"] or 0)
            taxable=price*qty
            gst_amt=taxable*gst/100
            current_mrp=float(x["mrp"] or 0)
            default_mult=(current_mrp/price) if price>0 and current_mrp>0 else (2.15 if abs(gst-5)<.001 else 2.25 if abs(gst-18)<.001 else 2.15)
            color_display=x.get("color") or "—"
            size_display=x.get("size") or "—"
            if str(x.get("attribute_type","")).upper()=="BOTH" and x.get("attribute_detail"):
                try:
                    det=json.loads(x.get("attribute_detail")) if isinstance(x.get("attribute_detail"),str) else x.get("attribute_detail")
                    size_display=" / ".join(f"{d.get('color','')}: {', '.join(d.get('sizes',[]))}" for d in det if d.get('color'))
                except Exception:
                    pass
            vals=[x["name"],x.get("hsn_code","") or "—",x.get("design_number","") or "—",
                  color_display,size_display,x["quantity"],money(price),f"{gst:g}%",
                  f"× {default_mult:.2f}",money(current_mrp),x["barcode"] or "NOT GENERATED"]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));it.setToolTip(str(v));self.t.setItem(r,c,it)

            mult=QDoubleSpinBox()
            mult.setRange(.01,99.99);mult.setDecimals(2);mult.setSingleStep(.05);mult.setPrefix("× ")
            mult.setValue(default_mult);mult.setReadOnly(True);mult.setButtonSymbols(QAbstractSpinBox.NoButtons)
            mult.setContextMenuPolicy(Qt.CustomContextMenu)
            mult.customContextMenuRequested.connect(lambda pos,rr=r:self.edit_multiplier(rr))
            self.t.setCellWidget(r,8,mult)


        self.t.setAlternatingRowColors(True)
        self.t.setMinimumHeight(380)
        self.print_btn.setEnabled(True)
        self.save_all_btn.setEnabled(True)
        self.t.resizeColumnsToContents()
        for c,w in enumerate([190,100,150,120,100,65,125,75,105,120,180]):
            self.t.setColumnWidth(c,w)


    def mrp_context_menu(self,pos):
        row=self.t.rowAt(pos.y())
        if row < 0 or row >= len(self.rows): return
        self.t.selectRow(row)
        menu=QMenu(self)
        edit=menu.addAction("EDIT MULTIPLIER")
        edit.triggered.connect(lambda:self.edit_multiplier(row))
        menu.exec(self.t.viewport().mapToGlobal(pos))


    def edit_multiplier(self,row):
        if not (0 <= row < len(self.rows)):
            return
        current=self.t.cellWidget(row,8)
        current_value=float(current.value()) if current else 2.15
        dlg=QDialog(self)
        dlg.setWindowTitle("EDIT MULTIPLIER")
        dlg.setModal(True)
        dlg.setFixedSize(440,250)
        dlg.setStyleSheet("""
            QDialog{background:#15171c;color:#f5f1e8}
            QLabel{color:#f5f1e8}
            QDoubleSpinBox{background:#101217;border:1px solid #454b57;border-radius:7px;padding:7px;font-size:15px}
            QPushButton{background:#252a32;color:#fff;border:1px solid #4b515c;border-radius:7px;padding:9px 20px;font-weight:600}
            QPushButton:hover{background:#343a45}
        """)
        lay=QVBoxLayout(dlg)
        title=QLabel("EDIT ITEM MULTIPLIER")
        title.setStyleSheet("font-size:19px;font-weight:700")
        lay.addWidget(title)
        item=QLabel(f'ITEM  •  {self.rows[row]["name"]}')
        item.setStyleSheet("color:#b8bec8;font-size:12px")
        lay.addWidget(item)
        sp=QDoubleSpinBox()
        sp.setRange(0.01,99.99);sp.setDecimals(2);sp.setSingleStep(0.05);sp.setValue(current_value);sp.setPrefix("× ");sp.setButtonSymbols(QAbstractSpinBox.NoButtons);sp.setKeyboardTracking(True);sp.lineEdit().selectAll()
        lay.addWidget(sp)
        hint=QLabel("Only this item will use the new multiplier.")
        hint.setStyleSheet("color:#8f96a3;font-size:11px")
        lay.addWidget(hint)
        lay.addStretch()
        buttons=QHBoxLayout();buttons.addStretch()
        cancel=QPushButton("CANCEL");ok=QPushButton("APPLY")
        buttons.addWidget(cancel);buttons.addWidget(ok);lay.addLayout(buttons)
        cancel.clicked.connect(dlg.reject);ok.clicked.connect(dlg.accept)
        if dlg.exec()!=QDialog.Accepted:
            return
        new_value=sp.value()
        self.t.cellWidget(row,8).setValue(new_value)
        self.recalculate_mrp(row,new_value)

    def recalculate_mrp(self,r,multiplier):
        if not (0 <= r < len(self.rows)):return
        price=float(self.rows[r]["rate"] or 0)
        mrp=round(price*float(multiplier),2)
        self.t.setItem(r,9,QTableWidgetItem(money(mrp)))

    def save_mrp(self,r,notify=True):
        if not (0 <= r < len(self.rows)): return False
        mult=self.t.cellWidget(r,8)
        if not mult: return False
        price=float(self.rows[r]["rate"] or 0)
        mrp=round(price*mult.value(),2)
        item_id=self.rows[r]["item_id"]
        db.set_item_mrp(item_id,mrp)
        self.rows[r]["mrp"]=mrp
        self.t.setItem(r,9,QTableWidgetItem(money(mrp)))
        code=self.rows[r].get("barcode")
        if not code or str(code).startswith("AUTO-"):
            code=db.next_barcode()
            db.set_item_barcode(item_id,code)
            self.rows[r]["barcode"]=code
            self.t.setItem(r,10,QTableWidgetItem(code))
        if notify:
            QMessageBox.information(self,"MRP SAVED","MRP AND BARCODE UPDATED FOR THIS ITEM.")
        return True


    def save_all_mrp(self):
        if not self.rows:
            return
        # Save every row in one click. No confirmation popup per item.
        for r in range(len(self.rows)):
            self.save_mrp(r,False)
        # Refresh visible multiplier/MRP/barcode values without asking anything.
        for r,x in enumerate(self.rows):
            mult=self.t.cellWidget(r,8)
            if mult:
                self.t.setItem(r,9,QTableWidgetItem(money(float(x.get("mrp") or 0))))
                self.t.setItem(r,10,QTableWidgetItem(str(x.get("barcode") or "NOT GENERATED")))
        self.save_all_btn.setText("✓  MRP SAVED")
        self.save_all_btn.setEnabled(False)

    def _expand_label_rows(self):
        expanded=[]
        for x in self.rows:
            try: qty=max(0,int(round(float(x.get("quantity") or 0))))
            except Exception: qty=0
            for _ in range(qty):
                expanded.append(x.copy())
        return expanded

    def _next_label_position(self):
        try: p=int(db.setting("barcode_next_position","1") or 1)
        except Exception: p=1
        return max(1,min(24,p))

    def _set_next_label_position(self,pos):
        p=((int(pos)-1)%24)+1
        db.set_setting("barcode_next_position",str(p))

    def print_labels(self):
        for r in range(len(self.rows)):
            self.save_mrp(r,False)
        labels=self._expand_label_rows()
        if not labels:
            return QMessageBox.warning(self,"BARCODE","NO PIECES FOUND IN THIS BILL.")
        start_pos=self._next_label_position()
        self.show_barcode_preview(labels,start_pos)

    @staticmethod
    def _style_code(rate):
        digits="".join(ch for ch in f"{float(rate):.0f}" if ch.isdigit())
        if len(digits)<4:
            digits=digits.zfill(4)
        rev=digits[::-1]
        return f"R{rev[:2]}P{rev[2:]}"

    @staticmethod
    def _color_code(color):
        s=str(color or "").strip()
        if not s:return "E1"
        if s.isdigit():return "E"+str(max(1,int(s)))
        parts=[p.strip() for p in re.split(r"[,/&+]+",s) if p.strip()]
        return "E"+str(max(1,len(parts)))

    @staticmethod
    def _date_code(iso_date):
        try:
            dt=datetime.strptime(str(iso_date),"%Y-%m-%d")
            return f"{dt.strftime('%y')}{dt.month}"
        except Exception:
            return ""

    @staticmethod
    def _attribute_codes(x):
        attr=str(x.get("attribute_type") or "").upper()
        raw_color=str(x.get("color") or "").strip()
        raw_size=str(x.get("size") or "").strip()
        if attr=="BOTH":
            # Stored as "BLUE: L, XL / GREEN: XXL"
            groups=[g.strip() for g in raw_color.split("/") if g.strip()]
            colors=[g.split(":",1)[0].strip() for g in groups if ":" in g]
            sizes=[]
            for g in groups:
                if ":" in g:
                    sizes.extend([v.strip() for v in g.split(":",1)[1].split(",") if v.strip()])
            return f"E{len(set(colors))}", f"M{len(set(sizes))}"
        if attr=="SIZE":
            n=len([v for v in re.split(r"[,/&+]+",raw_size) if v.strip()])
            return "E0", f"M{max(1,n)}"
        if attr=="COLOR":
            n=len([v for v in re.split(r"[,/&+]+",raw_color) if v.strip()])
            return f"E{max(1,n)}", "M0"
        return MRPBarcode._color_code(raw_color), "M0"

    @staticmethod
    def _attribute_code(x):
        ecode,mcode=MRPBarcode._attribute_codes(x)
        return ecode if ecode!="E0" else mcode


    def _label_data(self,x):
        gst=float(x.get("gst_rate") or 0)
        gcode=f"G{int(gst)}T" if gst.is_integer() else f"G{gst:g}T"
        return {
            "brand":"RANISAA EXCLUSIVE",
            "style":self._style_code(x.get("rate",0)),
            "color":self._attribute_codes(x)[0],
            "size_code":self._attribute_codes(x)[1],
            "party_code":str(x.get("_party_code") or "RLT").upper(),
            "date_code":self._date_code(x.get("_bill_date","")),
            "gst_code":gcode,
            "erp":str(x.get("barcode") or ""),
            "mrp":float(x.get("mrp") or 0),
        }

    def _saved_barcode_template(self):
        try:
            raw=db.setting("template_barcode","")
            data=json.loads(raw) if raw else {}
            if isinstance(data,dict) and data:
                data.pop("__page__",None)
                return data
        except Exception:
            pass
        return {}

    def show_barcode_preview(self,labels,start_pos=1):
        dlg=QDialog(self)
        dlg.setWindowTitle("BARCODE LABEL PREVIEW • A4 • 64 × 34 MM")
        dlg.setModal(True);dlg.resize(1180,820)
        dlg.setStyleSheet("""
            QDialog{background:#121419;color:#f5f1e8}
            QLabel{color:#f5f1e8}
            QPushButton{background:#252a32;color:#fff;border:1px solid #4b515c;border-radius:7px;padding:9px 18px;font-weight:600}
            QPushButton:hover{background:#343a45}
        """)
        lay=QVBoxLayout(dlg)
        h=QHBoxLayout();title=QLabel("BARCODE LABEL PREVIEW");title.setStyleSheet("font-size:20px;font-weight:700")
        h.addWidget(title);h.addStretch();h.addWidget(QLabel(f"A4 • 64 × 34 MM • {len(labels)} LABELS • START {start_pos}"));lay.addLayout(h)
        scroll=QScrollArea();scroll.setWidgetResizable(True)
        page=QWidget();grid=QGridLayout(page);grid.setSpacing(10);grid.setContentsMargins(28,20,28,20)
        # Preview cards are deliberately simple; the saved template itself is used for printing.
        for i,x in enumerate(labels[:24]):
            data=self._label_data(x)
            card=QFrame();card.setFixedSize(320,180);card.setStyleSheet("QFrame{background:#fff;color:#111;border:0}")
            cl=QVBoxLayout(card);cl.setContentsMargins(12,8,12,8);cl.setSpacing(2)
            brand=QLabel(data["brand"]);brand.setAlignment(Qt.AlignCenter);brand.setStyleSheet("color:#111;font-family:Georgia;font-size:15px;font-weight:700");cl.addWidget(brand)
            top=QHBoxLayout();a=QLabel(f'STYLE NO.\n{data["style"]}');a.setStyleSheet("color:#111;font-size:10px")
            b=QLabel(f'{data["color"]}     {data["party_code"]}\n{data["gst_code"]}');b.setAlignment(Qt.AlignRight);b.setStyleSheet("color:#111;font-size:10px")
            top.addWidget(a);top.addStretch();top.addWidget(b);cl.addLayout(top)
            bc=QLabel("|||||||||||||||||||||||||||||");bc.setAlignment(Qt.AlignCenter);bc.setStyleSheet("color:#111;font-size:20px;letter-spacing:1px");cl.addWidget(bc)
            code=QLabel(data["erp"]);code.setAlignment(Qt.AlignCenter);code.setStyleSheet("color:#111;font-size:9px");cl.addWidget(code)
            mr=QLabel(f'₹{data["mrp"]:,.0f}/-');mr.setAlignment(Qt.AlignCenter);mr.setStyleSheet("color:#111;font-size:16px;font-weight:800;padding:2px");cl.addWidget(mr)
            foot=QLabel("NO EXCHANGE • NO RETURN\nNO GUARANTEE ON ANY COLOR AND FABRIC\nPATHANKOT, PUNJAB  |  9459672222");foot.setAlignment(Qt.AlignCenter);foot.setStyleSheet("color:#111;font-size:6px;font-weight:600");cl.addWidget(foot)
            grid.addWidget(card,i//3,i%3)
        scroll.setWidget(page);lay.addWidget(scroll,1)
        note=QLabel(f"NEXT PRINT POSITION: {start_pos}  •  COMPUTER REMEMBERS THE LAST USED POSITION");note.setStyleSheet("color:#b9975b;font-weight:700");lay.addWidget(note)
        buttons=QHBoxLayout();buttons.addStretch();close=QPushButton("CLOSE");pr=QPushButton("PRINT NOW")
        buttons.addWidget(close);buttons.addWidget(pr);lay.addLayout(buttons)
        close.clicked.connect(dlg.reject);pr.clicked.connect(lambda:self.print_labels_direct(labels,dlg,start_pos));dlg.exec()

    def _draw_saved_template(self,c,x0,y0,dta):
        from reportlab.lib.units import mm
        from reportlab.graphics.barcode import code128
        from reportlab.graphics import renderPDF
        tmpl=self._saved_barcode_template()
        if not tmpl:
            # Safe fallback matching the current template.
            c.setFont("Times-Bold",11);c.drawCentredString(x0+32*mm,y0+31*mm,dta["brand"])
            c.setFont("Times-Roman",6);c.drawString(x0+5*mm,y0+25*mm,"STYLE NO.")
            c.setFont("Times-Bold",8);c.drawString(x0+8*mm,y0+21*mm,dta["style"])
            c.setFont("Times-Bold",8);c.drawString(x0+50*mm,y0+25*mm,dta["color"])
            bc=code128.Code128(dta["erp"],barHeight=6*mm,barWidth=.25*mm);renderPDF.draw(bc,c,x0+(64*mm-bc.width)/2,y0+15*mm)
            c.setFont("Times-Roman",5);c.drawCentredString(x0+32*mm,y0+13*mm,dta["erp"])
            c.setFont("Times-Bold",10);c.drawCentredString(x0+32*mm,y0+9*mm,f'₹{dta["mrp"]:,.0f}/-')
            c.setFont("Times-Bold",5);c.drawCentredString(x0+32*mm,y0+4*mm,"NO EXCHANGE NO RETURN")
            return
        keyvals={
            "BRAND":dta["brand"],"STYLE LABEL":"STYLE NO.","STYLE VALUE":dta["style"],"COLOR":dta["color"],
            "BARCODE VALUE":dta["erp"],"MRP":f'₹{dta["mrp"]:,.0f}/-',"NO EXCHANGE":"NO EXCHANGE NO RETURN",
            "NO GUARANTEE":"NO GUARANTEE ON ANY COLOR AND FABRIC","ADDRESS PHONE":"PATHANKOT, PUNJAB  |  9459672222",
            "RLT-DATE":f'{dta["party_code"]}-{dta["date_code"]}',"GST":dta["gst_code"]
        }
        from reportlab.pdfbase.pdfmetrics import stringWidth
        for key,d in tmpl.items():
            if not isinstance(d,dict) or not d.get("visible",True): continue
            xx=float(d.get("x",0))*mm; yy=float(d.get("y",0))*mm; ww=float(d.get("width",20))*mm
            text=keyvals.get(key,d.get("text", ""))
            if key=="BARCODE":
                try:
                    bc=code128.Code128(dta["erp"],barHeight=max(4,float(d.get("height",6)))*mm,barWidth=.22*mm)
                    renderPDF.draw(bc,c,x0+xx,y0+34*mm-yy-float(d.get("height",6))*mm)
                except Exception: pass
                continue
            try:
                qf=QFont();qf.fromString(str(d.get("font","")));size=max(4,qf.pointSize())
            except Exception:size=8
            fontname="Times-Bold" if "Bold" in str(d.get("font","")) else "Times-Roman"
            rot=float(d.get("rotation",0) or 0)
            c.saveState();c.translate(x0+xx,y0+34*mm-yy);c.rotate(-rot)
            c.setFont(fontname,size)
            # centered if the saved item is wider than the text; this keeps labels tidy.
            c.drawString(0,0,str(text))
            c.restoreState()

    def print_labels_direct(self,labels,parent,start_pos=1):
        try:
            import os,tempfile,subprocess
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            W,H=A4;lw,lh=64*mm,34*mm
            fd,path=tempfile.mkstemp(prefix="ranisaa_barcode_",suffix=".pdf");os.close(fd)
            c=canvas.Canvas(path,pagesize=A4)
            for i,x in enumerate(labels):
                slot=(start_pos-1+i)%24
                page_no=(start_pos-1+i)//24
                if i>0 and slot==0:c.showPage()
                col=slot%3;row=slot//3
                x0=(W-3*lw)/2+col*lw
                top_margin=(H-8*lh)/2
                y0=H-top_margin-(row+1)*lh
                self._draw_saved_template(c,x0,y0,self._label_data(x))
            c.showPage();c.save()
            # Persist the next physical position so the computer remembers where to continue.
            next_pos=((start_pos-1+len(labels))%24)+1
            self._set_next_label_position(next_pos)
            QMessageBox.information(parent,"PRINT READY",f"{len(labels)} barcode labels prepared.\nNext A4 position saved: {next_pos}.")
            # Direct print command on Windows; PDF is temporary and not a user-facing saved file.
            try:
                os.startfile(path,"print")
            except Exception:
                try: subprocess.Popen(["cmd","/c","start","","/print",path],shell=False)
                except Exception: QMessageBox.warning(parent,"PRINT","Windows could not start the printer command. The temporary print file was created.")
        except Exception:
            db.log_error(traceback.format_exc());QMessageBox.critical(parent,"PRINT ERROR","Could not prepare barcode print. Error logged.")


class BarcodeGenerator(MRPBarcode):
    """Simple popup-style barcode selection/print queue. MRP Generator is separate."""
    def __init__(self,user):
        super().__init__(user)

        # Hide every widget created by MRPBarcode. Its methods/template engine remain
        # available for barcode preview/printing, but its MRP UI is NOT shown here.
        for w in self.findChildren(QWidget):
            if w is not self:
                w.hide()

        self.setWindowTitle("BARCODE GENERATOR")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumSize(980,650)
        self.resize(1100,720)
        screen=QApplication.primaryScreen().availableGeometry()
        self.move(screen.center()-self.rect().center())
        self.queue=[]
        self.old_mode=False

        lay=self.layout()
        while lay.count():
            item=lay.takeAt(0)
            # Keep inherited widgets alive for the MRP/template methods, but remove
            # their old layout positions. They are already hidden above.
            if item.layout():
                sub=item.layout()
                while sub.count():
                    sub.takeAt(0)
        lay.setContentsMargins(18,16,18,16)
        lay.setSpacing(12)

        title=QLabel("BARCODE GENERATOR")
        title.setStyleSheet("font-size:23px;font-weight:800;letter-spacing:1px")
        lay.addWidget(title)

        mode=QHBoxLayout()
        self.purchase_mode=QPushButton("PURCHASE STOCK")
        self.old_mode_btn=QPushButton("OLD STOCK")
        for b in (self.purchase_mode,self.old_mode_btn):
            b.setMinimumHeight(42)
        self.purchase_mode.clicked.connect(lambda:self.set_old_mode(False))
        self.old_mode_btn.clicked.connect(lambda:self.set_old_mode(True))
        mode.addWidget(self.purchase_mode)
        mode.addWidget(self.old_mode_btn)
        mode.addStretch()
        lay.addLayout(mode)

        filters=QGroupBox("LOAD PURCHASE")
        g=QGridLayout(filters)
        g.setHorizontalSpacing(10);g.setVerticalSpacing(6)

        self.bg_party=QComboBox()
        self.bg_party.setEditable(True)
        self.bg_party.setCurrentIndex(-1)
        names=[x["name"] for x in db.parties()]
        self.bg_party.addItems(names)
        comp=QCompleter(names,self.bg_party)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.bg_party.setCompleter(comp)
        self.bg_party.lineEdit().setPlaceholderText("TYPE PARTY NAME")

        self.bg_invoice=UpperLineEdit()
        self.bg_invoice.setPlaceholderText("ENTER INVOICE NUMBER")

        self.bg_date=BillDateEdit()
        self.bg_date.setPlaceholderText("DDMMYY")

        self.bg_design=UpperLineEdit()
        self.bg_design.setPlaceholderText("SEARCH DESIGN NUMBER")

        self.bg_search=QPushButton("SEARCH DESIGN")
        self.bg_load=QPushButton("LOAD PURCHASE")
        self.bg_search.clicked.connect(self.search_stock)
        self.bg_load.clicked.connect(self.load_bill_stock)

        g.addWidget(QLabel("PARTY NAME"),0,0);g.addWidget(self.bg_party,1,0)
        g.addWidget(QLabel("INVOICE NUMBER"),0,1);g.addWidget(self.bg_invoice,1,1)
        g.addWidget(QLabel("DATE"),0,2);g.addWidget(self.bg_date,1,2)
        g.addWidget(QLabel("DESIGN NUMBER"),0,3);g.addWidget(self.bg_design,1,3)
        g.addWidget(self.bg_search,1,4);g.addWidget(self.bg_load,1,5)
        for c in range(6): g.setColumnStretch(c,1)
        lay.addWidget(filters)

        self.result=QTableWidget(0,9)
        self.result.setHorizontalHeaderLabels([
            "SELECT","DESIGN NUMBER","ITEM","HSN","COLOR / SIZE","QTY","GST %","MRP","SOURCE"
        ])
        self.result.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result.setAlternatingRowColors(True)
        self.result.verticalHeader().setDefaultSectionSize(40)
        self.result.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.result,2)

        controls=QHBoxLayout()
        self.select_all=QCheckBox("SELECT ALL")
        self.select_all.stateChanged.connect(self.toggle_all)
        self.add_selected_btn=QPushButton("ADD SELECTED TO LIST")
        self.add_selected_btn.clicked.connect(self.add_selected)
        self.selected_count=QLabel("0 selected")
        self.selected_count.setStyleSheet("font-weight:700;color:#b9975b")
        controls.addWidget(self.select_all)
        controls.addWidget(self.add_selected_btn)
        controls.addStretch()
        controls.addWidget(self.selected_count)
        lay.addLayout(controls)

        qbox=QGroupBox("BARCODE PRINT LIST")
        qlay=QVBoxLayout(qbox)
        self.queue_table=QTableWidget(0,6)
        self.queue_table.setHorizontalHeaderLabels([
            "DESIGN NUMBER","ITEM","COPIES","MRP","SOURCE","REMOVE"
        ])
        self.queue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.horizontalHeader().setStretchLastSection(True)
        self.queue_table.verticalHeader().setDefaultSectionSize(38)
        qlay.addWidget(self.queue_table)

        bottom=QHBoxLayout()
        self.queue_count=QLabel("0 labels in print list")
        self.queue_count.setStyleSheet("font-weight:700;color:#b9975b")
        self.view_list=QPushButton("VIEW BARCODE LIST")
        self.view_list.setMinimumHeight(46)
        self.view_list.setStyleSheet(
            "background:#b9975b;color:#111;font-weight:800;border-radius:8px;padding:9px 22px"
        )
        self.view_list.clicked.connect(self.view_queue)
        bottom.addWidget(self.queue_count);bottom.addStretch();bottom.addWidget(self.view_list)
        qlay.addLayout(bottom)
        lay.addWidget(qbox,2)

        note=QLabel("A4 • 64 × 34 MM • 24 LABELS / PAGE • NEXT PRINT POSITION IS REMEMBERED")
        note.setStyleSheet("color:#8f96a3;font-size:11px")
        lay.addWidget(note)

        self.set_old_mode(False)
        self._source_popup()

    def _source_popup(self):
        """Compact first-step source selector; the main barcode screen opens only after loading."""
        d=QDialog(self)
        d.setWindowTitle("BARCODE GENERATOR • SELECT SOURCE")
        d.setModal(True)
        d.setMinimumWidth(650)
        d.setStyleSheet("""
            QDialog{background:#101217;color:#f4f4f4;}
            QLabel{font-size:13px;}
            QLineEdit,QComboBox{min-height:40px;padding:6px 10px;}
            QPushButton{min-height:42px;padding:8px 18px;font-weight:700;}
        """)
        v=QVBoxLayout(d)
        title=QLabel("BARCODE GENERATOR")
        title.setStyleSheet("font-size:22px;font-weight:800;letter-spacing:1px;")
        v.addWidget(title)
        sub=QLabel("Select the stock source to begin")
        sub.setStyleSheet("color:#a7adb8;")
        v.addWidget(sub)

        tabs=QHBoxLayout()
        purchase_btn=QPushButton("PURCHASE / BILL")
        old_btn=QPushButton("OLD STOCK")
        tabs.addWidget(purchase_btn);tabs.addWidget(old_btn)
        v.addLayout(tabs)

        form=QFormLayout()
        party=QComboBox(); party.setEditable(True); party.setCurrentIndex(-1)
        names=[str(x.get("name") or "") for x in db.parties() if str(x.get("name") or "")]
        party.addItems(names)
        pc=QCompleter(names,party); pc.setCaseSensitivity(Qt.CaseInsensitive); pc.setFilterMode(Qt.MatchContains)
        party.setCompleter(pc); party.lineEdit().setPlaceholderText("ENTER PARTY NAME")
        inv=UpperLineEdit(); inv.setPlaceholderText("ENTER INVOICE NUMBER")
        date=BillDateEdit(); date.setPlaceholderText("DDMMYY")
        old_party=UpperLineEdit(); old_party.setPlaceholderText("ENTER PARTY CODE")
        old_design=UpperLineEdit(); old_design.setPlaceholderText("ENTER DESIGN NUMBER")
        try:
            codes=sorted({str(x.get("manufacturer_code") or "").strip().upper() for x in db.parties() if str(x.get("manufacturer_code") or "").strip()})
        except Exception: codes=[]
        oc=QCompleter(codes,old_party); oc.setCaseSensitivity(Qt.CaseInsensitive); oc.setFilterMode(Qt.MatchContains); old_party.setCompleter(oc)
        form.addRow("PARTY NAME",party); form.addRow("INVOICE NUMBER",inv); form.addRow("INVOICE DATE",date)
        form.addRow("PARTY CODE",old_party); form.addRow("DESIGN NUMBER",old_design)
        v.addLayout(form)

        hint=QLabel("Purchase: enter party, invoice and date.  Old Stock: enter party code and design number.")
        hint.setStyleSheet("color:#8f96a3;font-size:11px;")
        v.addWidget(hint)
        actions=QHBoxLayout()
        load=QPushButton("LOAD PURCHASE")
        search=QPushButton("SEARCH OLD STOCK")
        cancel=QPushButton("CANCEL")
        actions.addWidget(load); actions.addWidget(search); actions.addStretch(); actions.addWidget(cancel)
        v.addLayout(actions)

        def purchase_mode():
            self.set_old_mode(False)
            old_party.hide(); old_design.hide()
            form.labelForField(old_party).hide(); form.labelForField(old_design).hide()
            party.show(); inv.show(); date.show()
            form.labelForField(party).show(); form.labelForField(inv).show(); form.labelForField(date).show()
            load.show(); search.hide()
        def old_mode():
            self.set_old_mode(True)
            party.hide(); inv.hide(); date.hide()
            form.labelForField(party).hide(); form.labelForField(inv).hide(); form.labelForField(date).hide()
            old_party.show(); old_design.show()
            form.labelForField(old_party).show(); form.labelForField(old_design).show()
            load.hide(); search.show()
        def do_purchase():
            if not party.currentText().strip() or not inv.text().strip() or not date.text().strip():
                QMessageBox.warning(d,"BARCODE","ENTER PARTY NAME, INVOICE NUMBER AND INVOICE DATE.")
                return
            self.bg_party.setCurrentText(party.currentText().strip())
            self.bg_invoice.setText(inv.text().strip())
            self.bg_date.setText(date.text().strip())
            self.set_old_mode(False)
            d.accept()
            self.showMaximized()
            QTimer.singleShot(0,self.load_bill_stock)
        def do_old():
            if not old_party.text().strip() or not old_design.text().strip():
                QMessageBox.warning(d,"BARCODE","ENTER PARTY CODE AND DESIGN NUMBER.")
                return
            self.bg_party.setCurrentText(old_party.text().strip())
            self.bg_design.setText(old_design.text().strip())
            self.set_old_mode(True)
            d.accept()
            self.showMaximized()
            QTimer.singleShot(0,self.search_stock)
        purchase_btn.clicked.connect(purchase_mode); old_btn.clicked.connect(old_mode)
        load.clicked.connect(do_purchase); search.clicked.connect(do_old); cancel.clicked.connect(d.reject)
        purchase_mode()
        d.exec()
        if not d.result():
            self._startup_cancelled=True
            self.close()

    def set_old_mode(self,old):
        self.old_mode=bool(old)
        self.purchase_mode.setStyleSheet("font-weight:800" if not old else "")
        self.old_mode_btn.setStyleSheet("font-weight:800" if old else "")
        self.bg_invoice.setEnabled(not old)
        self.bg_date.setEnabled(not old)
        self.bg_load.setEnabled(not old)
        if old:
            self.bg_party.lineEdit().setPlaceholderText("ENTER PARTY CODE")
        else:
            self.bg_party.lineEdit().setPlaceholderText("TYPE PARTY NAME")
        self.result.setRowCount(0)
        self.select_all.setChecked(False)
        self.selected_count.setText("0 selected")

    def _purchase_date(self):
        text=self.bg_date.text().strip()
        if not text:
            return ""
        try:
            return self.bg_date.date_value()
        except Exception:
            QMessageBox.warning(self,"BARCODE","ENTER DATE AS DDMMYY. EXAMPLE: 101226.")
            self.bg_date.setFocus()
            return None

    def load_bill_stock(self):
        if self.old_mode:
            return
        party=self.bg_party.currentText().strip()
        inv=self.bg_invoice.text().strip()
        bill_date=self._purchase_date()
        if bill_date is None:return
        if not party or not inv or not bill_date:
            return QMessageBox.warning(
                self,"BARCODE","ENTER PARTY NAME, INVOICE NUMBER AND BILL DATE."
            )
        rows=db.barcode_design_search("",party,inv,bill_date)
        if not rows:
            return QMessageBox.warning(self,"BARCODE","PURCHASE BILL NOT FOUND.")
        self._show_results(rows,False)

    def search_stock(self):
        design=self.bg_design.text().strip()
        party=self.bg_party.currentText().strip()
        if self.old_mode:
            if not party and not design:
                self.result.setRowCount(0);return
            rows=db.barcode_old_stock_search(design,party)
            self._show_results(rows,True)
        else:
            inv=self.bg_invoice.text().strip()
            bill_date=""
            if self.bg_date.text().strip():
                bill_date=self._purchase_date()
                if bill_date is None:return
            rows=db.barcode_design_search(design,party,inv,bill_date)
            self._show_results(rows,False)

    def _show_results(self,rows,is_old):
        self.result.setRowCount(len(rows))
        for r,x in enumerate(rows):
            chk=QCheckBox()
            chk.setProperty("source_row",x)
            chk.stateChanged.connect(self.update_result_count)
            cell=QWidget();hl=QHBoxLayout(cell)
            hl.setContentsMargins(8,0,8,0);hl.addWidget(chk);hl.addStretch()
            self.result.setCellWidget(r,0,cell)

            design=x.get("design_number","") or "—"
            name=x.get("name","") or "—"
            color=x.get("color") or ""
            size=x.get("size") or ""
            attrs=" / ".join(v for v in (color,size) if v) or "—"
            qty=float(x.get("stock_qty") or x.get("quantity") or 0)
            mrp=float(x.get("mrp") or x.get("rate") or 0)
            source=("OLD STOCK • "+str(x.get("party_code",""))) if is_old else (
                f'{x.get("bill_number","")} • {x.get("supplier_name","")}'
            )
            hsn=str(x.get("hsn_code") or "—")
            gst=float(x.get("gst_rate") or 0)
            vals=[design,name,hsn,attrs,f"{qty:g}",f"{gst:g}%",money(mrp),source]
            for c,v in enumerate(vals,1):
                it=QTableWidgetItem(str(v));it.setToolTip(str(v));self.result.setItem(r,c,it)
        widths=[70,150,250,120,180,80,80,120,270]
        for c,w in enumerate(widths): self.result.setColumnWidth(c,w)
        self.update_result_count()

    def update_result_count(self,*_):
        n=0
        for r in range(self.result.rowCount()):
            cell=self.result.cellWidget(r,0)
            cb=cell.findChild(QCheckBox) if cell else None
            if cb and cb.isChecked():n+=1
        self.selected_count.setText(f"{n} selected")

    def toggle_all(self,state):
        checked=(state==Qt.Checked)
        for r in range(self.result.rowCount()):
            cell=self.result.cellWidget(r,0)
            cb=cell.findChild(QCheckBox) if cell else None
            if cb: cb.setChecked(checked)
        self.update_result_count()

    def _checked_rows(self):
        rows=[]
        for r in range(self.result.rowCount()):
            cell=self.result.cellWidget(r,0)
            cb=cell.findChild(QCheckBox) if cell else None
            if cb and cb.isChecked():
                x=cb.property("source_row")
                if isinstance(x,dict): rows.append(x)
        return rows

    def _is_unstitched(self,x):
        text=" ".join(str(x.get(k,"") or "") for k in ("name","category","item_name")).upper()
        return any(v in text for v in ("UNSTITCH","UNSTICH","UN-STITCH","UN STITCH"))

    def _ensure_barcode(self,x):
        item_id=x.get("item_id")
        code=str(x.get("barcode") or "")
        if not code or code.startswith("AUTO-") or code.startswith("OLD-"):
            code=db.next_barcode()
            if item_id: db.set_item_barcode(item_id,code)
        return code

    def _queue_item(self,x,is_old):
        y=dict(x)
        y["_party_code"]=str(x.get("party_code") or x.get("manufacturer_code") or "RLT").upper()
        y["_bill_date"]=str(x.get("bill_date") or "")
        if is_old:
            y["mrp"]=float(x.get("mrp") or x.get("rate") or 0)
            y["gst_rate"]=float(x.get("gst_rate") or 0)
            y["rate"]=float(x.get("rate") or x.get("mrp") or 0)
            y["barcode"]=self._ensure_barcode(y)
            y["_source"]="OLD STOCK"
        else:
            y["_source"]=str(x.get("bill_number") or "PURCHASE")
        y["_copies"]=2 if self._is_unstitched(y) else 1
        return y

    def add_selected(self):
        selected=self._checked_rows()
        if not selected:
            return QMessageBox.warning(self,"BARCODE LIST","SELECT AT LEAST ONE ITEM.")
        for x in selected:
            self.add_to_queue(x,self.old_mode)
        self.select_all.setChecked(False)
        self.update_result_count()

    def add_to_queue(self,x,is_old=False):
        y=self._queue_item(x,is_old)
        key=(str(y.get("design_number","")),str(y.get("_source","")),str(y.get("item_id","")),str(y.get("old_id","")))
        for i,q in enumerate(self.queue):
            qkey=(str(q.get("design_number","")),str(q.get("_source","")),str(q.get("item_id","")),str(q.get("old_id","")))
            if qkey==key:
                self.queue[i]=y;self.refresh_queue();return
        self.queue.append(y);self.refresh_queue()

    def refresh_queue(self):
        self.queue_table.setRowCount(len(self.queue))
        for r,x in enumerate(self.queue):
            vals=[x.get("design_number",""),x.get("name","") or "OLD STOCK",
                  x.get("_copies",1),money(float(x.get("mrp") or x.get("rate") or 0)),x.get("_source","")]
            for c,v in enumerate(vals): self.queue_table.setItem(r,c,QTableWidgetItem(str(v)))
            rm=QPushButton("REMOVE")
            rm.clicked.connect(lambda _,rr=r:self.remove_queue(rr))
            self.queue_table.setCellWidget(r,5,rm)
        total=sum(int(x.get("_copies",1)) for x in self.queue)
        self.queue_count.setText(f"{total} labels in print list")

    def remove_queue(self,r):
        if 0<=r<len(self.queue):
            self.queue.pop(r);self.refresh_queue()

    def view_queue(self):
        if not self.queue:
            return QMessageBox.warning(self,"BARCODE LIST","ADD ITEMS TO THE PRINT LIST FIRST.")
        self.queue.sort(key=lambda x:str(x.get("design_number","")))
        self.refresh_queue()
        labels=[]
        for x in self.queue:
            for _ in range(int(x.get("_copies",1))): labels.append(dict(x))
        start=self._next_label_position()
        self.show_barcode_preview(labels,start)


class Billing(QWidget):
    def __init__(self,user):
        super().__init__();self.user=user;self.rows=[];self.setWindowTitle("BILLING");self.resize(1280,800);l=QVBoxLayout(self)
        g=QGridLayout();self.bill=QLineEdit(db.next_no("sale"));self.dt=QLineEdit(QDate.currentDate().toString("dd-MM-yyyy"));self.dt.setInputMask("00-00-0000");self.mob=QLineEdit();self.name=QLineEdit()
        self.mob.editingFinished.connect(self.fetch_customer)
        for lab,w,r,c in[("Bill No.",self.bill,0,0),("Date (DDMMYYYY)",self.dt,0,2),("Customer Mobile",self.mob,1,0),("Customer Name",self.name,1,2)]:g.addWidget(QLabel(lab),r,c);g.addWidget(w,r,c+1)
        l.addLayout(g)
        box=QGroupBox("SCAN / ENTER BARCODE");gg=QGridLayout(box);self.bar=QLineEdit();self.bar.setPlaceholderText("SCAN WITH GUN OR TYPE BARCODE");self.bar.returnPressed.connect(self.add);self.bar.setFocus()
        self.qty=QLineEdit("1");self.rate=QLineEdit();self.disc=QLineEdit("0");add=QPushButton("ADD ITEM");add.clicked.connect(self.add)
        for i,(lab,w) in enumerate([("Barcode",self.bar),("Qty",self.qty),("Price GST Inclusive",self.rate),("Discount %",self.disc)]):gg.addWidget(QLabel(lab),0,i);gg.addWidget(w,1,i)
        gg.addWidget(add,1,4);l.addWidget(box)
        self.t=QTableWidget(0,9);self.t.setHorizontalHeaderLabels(["BARCODE","HSN","ITEM","QTY","MRP","RATE GST INCL.","DISCOUNT ₹","GST","AMOUNT"]);self.t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);l.addWidget(self.t)
        self.sum=QLabel();l.addWidget(self.sum)
        b=QPushButton("PRINT BILL");b.clicked.connect(self.print_bill);l.addWidget(b)
        self.calc()
    def fetch_customer(self):
        c=db.customer_by_mobile(self.mob.text());self.name.setText(c["name"] if c else "")
    def add(self):
        code=self.bar.text().strip();x=db.item_barcode(code)
        try:q=float(self.qty.text() or 1);dp=float(self.disc.text() or 0)
        except:return QMessageBox.warning(self,"BILLING","Enter valid quantity/discount.")
        if not x or q<=0 or q>x["stock_qty"]:return QMessageBox.warning(self,"BILLING","Barcode not found or insufficient stock.")
        gross=float(self.rate.text() or x["mrp"] or x["sale_price"] or 0)
        if gross<=0:return QMessageBox.warning(self,"BILLING","MRP/Sale price is not set for this item.")
        if not 0<=dp<=100:return QMessageBox.warning(self,"BILLING","Discount must be between 0 and 100.")
        discount=gross*q*dp/100;after=gross*q-discount;gst_rate=float(x["gst_rate"] or 0);taxable=after/(1+gst_rate/100) if gst_rate else after;gst=after-taxable
        self.rows.append({"id":x["id"],"bar":x["barcode"],"hsn":x["hsn_code"],"name":x["name"],"qty":q,"mrp":float(x["mrp"] or 0),"rate":gross,"gst":gst_rate,"disc":discount,"amount":taxable,"ga":gst});self.refresh();self.bar.clear();self.qty.setText("1");self.rate.clear();self.disc.setText("0");self.bar.setFocus()
    def refresh(self):
        self.t.setRowCount(len(self.rows))
        for r,x in enumerate(self.rows):
            vals=[x["bar"],x["hsn"],x["name"],x["qty"],money(x["mrp"]),money(x["rate"]),money(x["disc"]),money(x["ga"]),money(x["amount"]+x["ga"])]
            for c,v in enumerate(vals):self.t.setItem(r,c,QTableWidgetItem(str(v)))
        self.calc()
    def calc(self):
        gross=sum(x["qty"]*x["rate"] for x in self.rows);dis=sum(x["disc"] for x in self.rows);ga=sum(x["ga"] for x in self.rows);total=gross-dis
        self.sum.setText(f"MRP TOTAL ₹{gross:,.2f} | DISCOUNT ₹{dis:,.2f} | GST ₹{ga:,.2f} (included) | GRAND TOTAL ₹{total:,.2f}")
    def print_bill(self):
        if not self.rows:return QMessageBox.warning(self,"BILLING","Add at least one item first.")
        pay,ok=QInputDialog.getItem(self,"Payment","Select payment mode:",["CASH","CARD","UPI"],0,False)
        if not ok:return
        try:typed_date=datetime.strptime(self.dt.text(),"%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:return QMessageBox.warning(self,"BILLING","Enter date as DDMMYYYY. Hyphens are automatic.")
        gross=sum(x["qty"]*x["rate"] for x in self.rows);dis=sum(x["disc"] for x in self.rows);ga=sum(x["ga"] for x in self.rows);total=gross-dis
        try:
            sid=db.sale({"bill":self.bill.text().strip(),"name":self.name.text(),"mobile":self.mob.text(),"address":"","date":typed_date,"time":datetime.now().strftime("%H:%M:%S"),"subtotal":gross,"discount":dis,"gst":ga,"total":total,"pay":pay,"user":self.user["id"]},self.rows)
            p=self.make_bill_pdf(sid,pay,total,dis,ga,typed_date)
            QMessageBox.information(self,"BILL PRINTED & SAVED",f"Payment: {pay}\nBill saved.\nPDF: {p}")
            try:os.startfile(p,"print")
            except:os.startfile(p)
            self.rows=[];self.bill.setText(db.next_no("sale"));self.refresh()
        except Exception as e:
            db.log_error(traceback.format_exc());QMessageBox.critical(self,"BILLING","Could not save/print bill. Check logs/error.log.")
    def make_bill_pdf(self,sid,pay,total,dis,ga,date):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        p=str(Path(db.ROOT)/"exports"/f"bill_{self.bill.text().strip()}.pdf");c=canvas.Canvas(p,pagesize=A4);W,H=A4
        template=db.setting("bill_template_path","")
        if template and Path(template).exists() and Path(template).suffix.lower() in (".png",".jpg",".jpeg"):c.drawImage(ImageReader(template),0,0,width=W,height=H,mask="auto")
        y=H-20*mm;c.setFont("Helvetica-Bold",15);c.drawString(20*mm,y,db.setting("company_name","RANISAA EXCLUSIVE"));y-=10*mm
        c.setFont("Helvetica",9);c.drawString(20*mm,y,f"Bill No: {self.bill.text()}    Date: {date}    Payment: {pay}");y-=8*mm
        c.drawString(20*mm,y,f"Customer: {self.name.text()}    Mobile: {self.mob.text()}");y-=8*mm
        c.line(15*mm,y,195*mm,y);y-=6*mm
        c.setFont("Helvetica-Bold",8);c.drawString(16*mm,y,"Barcode");c.drawString(45*mm,y,"HSN");c.drawString(70*mm,y,"Item");c.drawString(125*mm,y,"Qty");c.drawString(140*mm,y,"Rate");c.drawString(160*mm,y,"Disc");c.drawString(178*mm,y,"Amount");y-=5*mm
        c.setFont("Helvetica",8)
        for x in self.rows:
            c.drawString(16*mm,y,str(x["bar"])[:18]);c.drawString(45*mm,y,str(x["hsn"])[:12]);c.drawString(70*mm,y,str(x["name"])[:28]);c.drawRightString(135*mm,y,str(x["qty"]));c.drawRightString(155*mm,y,f"{x['rate']:.2f}");c.drawRightString(175*mm,y,f"{x['disc']:.2f}");c.drawRightString(194*mm,y,f"{x['amount']+x['ga']:.2f}");y-=5*mm
        y-=3*mm;c.drawString(135*mm,y,f"Discount: ₹{dis:,.2f}");y-=5*mm;c.drawString(135*mm,y,f"GST Included: ₹{ga:,.2f}");y-=5*mm;c.setFont("Helvetica-Bold",10);c.drawString(135*mm,y,f"TOTAL: ₹{total:,.2f}");c.save();return p

class OldStockEntry(QWidget):
    def __init__(self,user):
        super().__init__()
        self.user=user
        self.setWindowTitle("OLD STOCK ENTRY")
        self.setMinimumSize(980,680)
        self.resize(1180,760)
        self.setStyleSheet("""
            QWidget{background:#101217;color:#f4f1ea}
            QGroupBox{border:1px solid #363c47;border-radius:12px;margin-top:14px;padding:18px 14px 14px;font-weight:700;color:#e9e4da}
            QGroupBox::title{subcontrol-origin:margin;left:16px;padding:0 8px;color:#d9c39a}
            QLineEdit,QDoubleSpinBox,QComboBox{
                background:#0b0d10;border:1px solid #3e4552;border-radius:8px;
                min-height:46px;padding:0 12px;color:#f4f1ea;font-size:15px
            }
            QLineEdit:focus,QDoubleSpinBox:focus,QComboBox:focus{border:1px solid #8d7750}
            QLabel#field{font-size:12px;font-weight:700;color:#aeb4bf;letter-spacing:1px}
            QLabel#title{font-size:28px;font-weight:800}
            QLabel#sub{font-size:12px;color:#8f96a3}
            QPushButton{
                background:#252b34;border:1px solid #4b5360;border-radius:8px;
                min-height:46px;padding:0 24px;color:#fff;font-weight:700
            }
            QPushButton:hover{background:#313844}
            QTableWidget{background:#0b0d10;border:1px solid #2d333d;gridline-color:#292e37}
            QHeaderView::section{background:#20252d;color:#fff;padding:12px;font-weight:700;border:0}
            QTableWidget::item{padding:8px}
        """)
        l=QVBoxLayout(self);l.setContentsMargins(26,22,26,24);l.setSpacing(14)

        top=QHBoxLayout()
        title=QLabel("OLD STOCK ENTRY");title.setObjectName("title");top.addWidget(title)
        top.addStretch()
        sub=QLabel("LEGACY STOCK • ADMIN");sub.setObjectName("sub");top.addWidget(sub)
        l.addLayout(top)

        box=QGroupBox("STOCK DETAILS");g=QGridLayout(box);g.setHorizontalSpacing(14);g.setVerticalSpacing(9)
        self.design=UpperLineEdit();self.design.setPlaceholderText("ENTER DESIGN NUMBER")
        self.party=UpperLineEdit();self.party.setPlaceholderText("ENTER PARTY CODE")
        try:
            party_codes=sorted({str(x.get("manufacturer_code") or "").strip().upper() for x in db.parties() if str(x.get("manufacturer_code") or "").strip()})
        except Exception:
            party_codes=[]
        self.party_completer=QCompleter(party_codes,self.party)
        self.party_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.party_completer.setFilterMode(Qt.MatchContains)
        self.party_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.party.setCompleter(self.party_completer)
        self.qty=OldStockSpinBox();self.qty.setRange(0,999999);self.qty.setDecimals(2);self.qty.setValue(0);self.qty.setButtonSymbols(QAbstractSpinBox.NoButtons);self.qty.setSpecialValueText(" ");self.qty.lineEdit().clear()
        self.rate=OldStockSpinBox();self.rate.setRange(0,99999999);self.rate.setDecimals(2);self.rate.setButtonSymbols(QAbstractSpinBox.NoButtons);self.rate.setSpecialValueText(" ");self.rate.lineEdit().clear()
        self.gst=QComboBox();self.gst.addItems(["5%","12%","18%"])
        try:
            self.qty.setSpecialValueText(" ")
            self.rate.setSpecialValueText(" ")
        except Exception:
            pass
        self.attr_type=QComboBox();self.attr_type.addItems(["NONE","COLOR","SIZE","BOTH"])
        self.attr_values=UpperLineEdit();self.attr_values.setPlaceholderText("COLOR: BLUE,GREEN  |  SIZE: L,XL  |  BOTH: BLUE L,XL / GREEN XXL")
        fields=[("DESIGN NUMBER",self.design),("PARTY CODE",self.party),("QUANTITY",self.qty),("RATE / PRICE",self.rate),("GST",self.gst),
                ("TYPE",self.attr_type),("COLOR / SIZE",self.attr_values)]
        for i,(lab,w) in enumerate(fields):
            q=QLabel(lab);q.setObjectName("field");g.addWidget(q,0,i);g.addWidget(w,1,i)
        for i in range(len(fields)): g.setColumnStretch(i,1)
        l.addWidget(box)

        note=QLabel("Old stock is added directly to Stock. Right-click the stock item to view its legacy details.")
        note.setObjectName("sub");l.addWidget(note)

        b=QPushButton("＋  ADD OLD STOCK")
        b.setMinimumHeight(50);b.clicked.connect(self.add);l.addWidget(b)

        head=QHBoxLayout()
        h=QLabel("RECENT OLD STOCK ENTRIES");h.setStyleSheet("font-size:14px;font-weight:800")
        head.addWidget(h);head.addStretch();l.addLayout(head)

        self.t=QTableWidget(0,7)
        self.t.setHorizontalHeaderLabels(["DESIGN NUMBER","PARTY CODE","QTY","RATE / PRICE","GST","COLOR","SIZE / COLOR MAPPING"])
        self.t.setEditTriggers(QAbstractItemView.NoEditTriggers);self.t.setAlternatingRowColors(True)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t.horizontalHeader().setStretchLastSection(True)
        for i,w in enumerate([260,220,130,190,120]): self.t.setColumnWidth(i,w)
        self.t.verticalHeader().setDefaultSectionSize(42)
        l.addWidget(self.t,1)
        self.load()

    def add(self):
        try:
            db.add_old_stock(self.design.text(),self.party.text(),self.qty.value(),self.rate.value(),
                             float(self.gst.currentText().replace("%","")),
                             self.attr_type.currentText(),self.attr_values.text())
            self.load()
            self.design.clear();self.party.clear();self.qty.setValue(0);self.qty.lineEdit().clear();self.rate.setValue(0);self.rate.lineEdit().clear()
            self.gst.setCurrentIndex(0);self.attr_type.setCurrentIndex(0);self.attr_values.clear()
            self.design.setFocus()
            QMessageBox.information(self,"OLD STOCK ADDED","OLD STOCK HAS BEEN ADDED TO STOCK.")
        except Exception as e:
            QMessageBox.critical(self,"OLD STOCK","COULD NOT ADD OLD STOCK.\n\n"+str(e))

    def load(self):
        rs=db.old_stock_entries();self.t.setRowCount(len(rs))
        for r,x in enumerate(rs):
            vals=[x["design_number"],x["party_code"],f'{float(x["quantity"]):g}',money(x["rate"]),f'{float(x["gst_rate"]):g}%',
                   x.get("color") or "—",x.get("size") or "—"]
            for c,v in enumerate(vals):
                it=QTableWidgetItem(str(v));it.setToolTip(str(v));self.t.setItem(r,c,it)


class Stock(QWidget):
    def __init__(self,user):
        super().__init__()
        self.user=user
        self.setWindowTitle("STOCK")
        self.setWindowState(Qt.WindowMaximized)
        l=QVBoxLayout(self)
        title=QLabel("STOCK")
        title.setStyleSheet("font-size:22px;font-weight:700")
        l.addWidget(title)

        self.s=QLineEdit()
        self.s.setPlaceholderText("SEARCH ITEM / BARCODE / DESIGN")
        self.s.setMinimumHeight(42)
        l.addWidget(self.s)

        self.t=QTableWidget(0,9 if user["role"]=="admin" else 8)
        if user["role"]=="admin":
            headers=["BARCODE","ITEM","DESIGN NUMBER","COLOR","SIZE","PURCHASE RATE","MRP","GST %","STOCK QTY"]
        else:
            headers=["BARCODE","ITEM","DESIGN NUMBER","COLOR","SIZE","MRP","GST %","STOCK QTY"]
        self.t.setHorizontalHeaderLabels(headers)
        self.t.setAlternatingRowColors(True)
        self.t.setWordWrap(False)
        self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t.setContextMenuPolicy(Qt.CustomContextMenu)
        if self.user["role"]=="admin":
            self.t.customContextMenuRequested.connect(self.stock_context_menu)
        self.t.verticalHeader().setDefaultSectionSize(38)
        self.t.horizontalHeader().setMinimumSectionSize(90)
        self.t.horizontalHeader().setStretchLastSection(True)
        l.addWidget(self.t,1)

        self.s.textChanged.connect(self.load)
        self.load()

    def stock_context_menu(self,pos):
        row=self.t.rowAt(pos.y())
        if row < 0:return
        self.t.selectRow(row)
        barcode_item=self.t.item(row,0)
        if not barcode_item:return
        x=db.item_barcode(barcode_item.text().strip())
        if not x:return
        menu=QMenu(self)
        view=menu.addAction("VIEW SOURCE BILL")
        view.triggered.connect(lambda:self.view_source_bill(x["id"]))
        menu.exec(self.t.viewport().mapToGlobal(pos))

    def view_source_bill(self,item_id):
        old=db.old_stock_by_item(item_id)
        if old:
            dlg=QDialog(self);dlg.setWindowTitle("SOURCE • OLD STOCK");dlg.setModal(True);dlg.setFixedSize(620,390)
            dlg.setStyleSheet("""
                QDialog{background:#121419;color:#f5f1e8}
                QLabel{color:#f5f1e8}
                QLabel#section{font-size:10px;color:#aeb4bf;letter-spacing:1px;font-weight:700}
                QLabel#value{font-size:15px;font-weight:650}
                QFrame{background:#191d24;border:1px solid #303641;border-radius:10px}
                QPushButton{background:#252a32;color:#fff;border:1px solid #4b515c;border-radius:7px;padding:9px 22px;font-weight:600}
            """)
            lay=QVBoxLayout(dlg);h=QHBoxLayout()
            title=QLabel("SOURCE • OLD STOCK");title.setStyleSheet("font-size:21px;font-weight:800");h.addWidget(title);h.addStretch();lay.addLayout(h)
            card=QFrame();g=QGridLayout(card)
            def fld(r,c,a,b):
                q=QVBoxLayout();la=QLabel(a);la.setObjectName("section");lb=QLabel(str(b));lb.setObjectName("value");q.addWidget(la);q.addWidget(lb);g.addLayout(q,r,c)
            fld(0,0,"SOURCE","OLD STOCK");fld(0,1,"DESIGN NUMBER",old["design_number"])
            fld(1,0,"PARTY CODE",old["party_code"]);fld(1,1,"GST",f'{float(old["gst_rate"]):g}%')
            fld(2,0,"RATE / PRICE",money(old["rate"]));fld(2,1,"QUANTITY",f'{old["quantity"]} PCS')
            lay.addWidget(card);lay.addStretch();close=QPushButton("CLOSE");close.clicked.connect(dlg.accept);rr=QHBoxLayout();rr.addStretch();rr.addWidget(close);lay.addLayout(rr);dlg.exec()
            return
        x=db.item_source_purchase(item_id)
        if not x or not x.get("purchase_id"):
            return QMessageBox.information(self,"SOURCE BILL","NO PURCHASE SOURCE BILL FOUND FOR THIS ITEM.")

        dlg=QDialog(self)
        dlg.setWindowTitle("SOURCE BILL")
        dlg.setModal(True)
        dlg.setFixedSize(620,440)
        dlg.setStyleSheet("""
            QDialog{background:#121419;color:#f5f1e8}
            QLabel{color:#f5f1e8}
            QLabel#section{font-size:11px;color:#aeb4bf;letter-spacing:1px;font-weight:700}
            QLabel#value{font-size:14px;font-weight:600}
            QFrame{background:#191d24;border:1px solid #303641;border-radius:10px}
            QPushButton{background:#252a32;color:#fff;border:1px solid #4b515c;border-radius:7px;padding:9px 22px;font-weight:600}
            QPushButton:hover{background:#343a45}
        """)

        lay=QVBoxLayout(dlg)
        top=QHBoxLayout()
        title=QLabel("SOURCE BILL")
        title.setStyleSheet("font-size:22px;font-weight:700")
        top.addWidget(title)
        top.addStretch()
        party=QLabel(str(x["supplier_name"] or "—"))
        party.setStyleSheet("font-size:15px;font-weight:700;color:#d9c39a")
        top.addWidget(party)
        lay.addLayout(top)

        sub=QLabel("PURCHASE TRACEABILITY")
        sub.setObjectName("section")
        lay.addWidget(sub)

        card=QFrame()
        grid=QGridLayout(card)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(15)

        def add_field(r,c,label,value):
            l=QVBoxLayout()
            a=QLabel(label.upper());a.setObjectName("section")
            b=QLabel(str(value));b.setObjectName("value")
            b.setWordWrap(True)
            l.addWidget(a);l.addWidget(b)
            grid.addLayout(l,r,c)

        add_field(0,0,"ITEM",x["name"])
        add_field(0,1,"DESIGN NUMBER",x["design_number"] or "—")
        add_field(1,0,"BARCODE",x["barcode"])
        add_field(1,1,"STOCK",f'{x["stock_qty"]} PCS')
        add_field(2,0,"MRP",money(x["mrp"]))
        add_field(2,1,"GST",f'{float(x["gst_rate"] or 0):g}%')
        add_field(3,0,"INVOICE NUMBER",x["bill_number"])
        raw_date=str(x["bill_date"] or "")
        try:
            display_date=datetime.strptime(raw_date,"%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            display_date=raw_date
        add_field(3,1,"PURCHASE DATE",display_date)
        lay.addWidget(card)

        note=QLabel("THIS ITEM WAS RECEIVED THROUGH THE PURCHASE BILL SHOWN ABOVE.")
        note.setStyleSheet("font-size:11px;color:#8f96a3;padding-top:4px")
        lay.addWidget(note)
        lay.addStretch()

        close=QPushButton("CLOSE")
        close.clicked.connect(dlg.accept)
        row=QHBoxLayout();row.addStretch();row.addWidget(close)
        lay.addLayout(row)
        dlg.exec()


    def load(self):
        q=self.s.text().strip().lower()
        rs=db.items()
        rs=[x for x in rs if not q or any(q in str(x.get(k,"")).lower()
            for k in ("barcode","name","design_number","color","size"))]
        self.t.setRowCount(len(rs))
        admin=self.user["role"]=="admin"
        for r,x in enumerate(rs):
            color_display=x.get("color") or "—"
            size_display=x.get("size") or "—"
            if str(x.get("attribute_type","")).upper()=="BOTH" and x.get("attribute_detail"):
                try:
                    det=json.loads(x.get("attribute_detail")) if isinstance(x.get("attribute_detail"),str) else x.get("attribute_detail")
                    size_display=" / ".join(f"{d.get('color','')}: {', '.join(d.get('sizes',[]))}" for d in det if d.get('color'))
                except Exception:
                    pass
            if admin:
                vals=[x["barcode"],x["name"],x["design_number"],
                      color_display,size_display,
                      money(x["purchase_price"]),money(x["mrp"]),f'{float(x["gst_rate"] or 0):g}%',x["stock_qty"]]
            else:
                vals=[x["barcode"],x["name"],x["design_number"],
                      color_display,size_display,
                      money(x["mrp"]),f'{float(x["gst_rate"] or 0):g}%',x["stock_qty"]]
            for c,v in enumerate(vals):
                item=QTableWidgetItem(str(v))
                item.setToolTip(str(v))
                self.t.setItem(r,c,item)

        # Readability: sensible widths on a maximized window.
        widths = [150,240,170,150,150,140,120,100,130] if admin else [150,260,170,150,150,120,100,130]
        for i,w in enumerate(widths):
            self.t.setColumnWidth(i,w)

class Reports(QWidget):
    def __init__(self,user):
        super().__init__();self.setWindowTitle("REPORTS");self.resize(1100,700);l=QVBoxLayout(self);g=QHBoxLayout();self.a=QDateEdit(QDate.currentDate().addDays(-30));self.b=QDateEdit(QDate.currentDate());run=QPushButton("RUN");ex=QPushButton("EXPORT EXCEL");run.clicked.connect(self.load);ex.clicked.connect(self.xlsx);g.addWidget(self.a);g.addWidget(self.b);g.addWidget(run);g.addWidget(ex);l.addLayout(g);self.t=QTableWidget(0,7);self.t.setHorizontalHeaderLabels(["BILL","DATE","TIME","SUBTOTAL","DISCOUNT","GST","TOTAL"]);l.addWidget(self.t);self.load()
    def load(self):
        rs=db.sales_report(self.a.date().toString("yyyy-MM-dd"),self.b.date().toString("yyyy-MM-dd"));self.t.setRowCount(len(rs))
        for r,x in enumerate(rs):[self.t.setItem(r,c,QTableWidgetItem(str(v))) for c,v in enumerate([x["bill_number"],x["bill_date"],x["bill_time"],money(x["subtotal"]),money(x["discount"]),money(x["tax_amount"]),money(x["total_amount"])])]
    def xlsx(self):
        p=QFileDialog.getSaveFileName(self,"Save Excel",str(Path(db.ROOT)/"exports/sales_report.xlsx"),"Excel (*.xlsx)")[0]
        if not p:return
        from openpyxl import Workbook
        wb=Workbook();w=wb.active;w.title="Sales";w.append(["Bill","Date","Time","Subtotal","Discount","GST","Total"])
        for x in db.sales_report(self.a.date().toString("yyyy-MM-dd"),self.b.date().toString("yyyy-MM-dd")):w.append([x["bill_number"],x["bill_date"],x["bill_time"],x["subtotal"],x["discount"],x["tax_amount"],x["total_amount"]])
        wb.save(p);QMessageBox.information(self,"EXPORT","Excel file created.")

class Customers(QWidget):
    def __init__(self,user):
        super().__init__();self.setWindowTitle("CUSTOMERS");self.resize(700,550);l=QVBoxLayout(self);self.t=QTableWidget(0,2);self.t.setHorizontalHeaderLabels(["CUSTOMER NAME","MOBILE"]);l.addWidget(self.t)
        for r,x in enumerate(db.customers()):self.t.insertRow(r);self.t.setItem(r,0,QTableWidgetItem(str(x["name"])));self.t.setItem(r,1,QTableWidgetItem(str(x["mobile"])))

class Parties(QDialog):
    def __init__(self,user):
        super().__init__();self.user=user;self.setWindowTitle("PARTIES");self.setModal(True);self.setFixedSize(760,520)
        screen=QApplication.primaryScreen().availableGeometry();self.move(screen.center()-self.rect().center())
        l=QVBoxLayout(self);l.setContentsMargins(18,16,18,16);l.setSpacing(10)
        title=QLabel("PARTIES");title.setAlignment(Qt.AlignCenter);title.setStyleSheet("font-size:24px;font-weight:700;letter-spacing:1px");l.addWidget(title)
        g=QGridLayout();g.setHorizontalSpacing(12);g.setVerticalSpacing(8);self.n=UpperLineEdit();self.n.setPlaceholderText("PARTY NAME");self.g=UpperLineEdit();self.g.setPlaceholderText("GST NUMBER")
        self.mcode=UpperLineEdit();self.mcode.setPlaceholderText("MANUFACTURER CODE  e.g. RLT")
        for w in (self.n,self.g,self.mcode): w.setMinimumHeight(42)
        g.addWidget(QLabel("PARTY NAME"),0,0);g.addWidget(self.n,0,1)
        g.addWidget(QLabel("GST NUMBER"),1,0);g.addWidget(self.g,1,1)
        g.addWidget(QLabel("MANUFACTURER CODE"),2,0);g.addWidget(self.mcode,2,1)
        g.setColumnStretch(0,0);g.setColumnStretch(1,1);l.addLayout(g)
        save=QPushButton("SAVE PARTY");save.clicked.connect(self.save);back=QPushButton("BACK");back.clicked.connect(self.reject)
        for b in (save,back): b.setMinimumHeight(42)
        l.addWidget(save);l.addWidget(back)
        self.t=QTableWidget(0,4);self.t.setHorizontalHeaderLabels(["PARTY NAME","GST NUMBER","MANUFACTURER CODE","ACTION"]);h=self.t.horizontalHeader();h.setSectionResizeMode(0,QHeaderView.Stretch);h.setSectionResizeMode(1,QHeaderView.Stretch);h.setSectionResizeMode(2,QHeaderView.Stretch);h.setSectionResizeMode(3,QHeaderView.Fixed);h.resizeSection(3,112)
        self.t.setAlternatingRowColors(True);self.t.setSelectionMode(QAbstractItemView.NoSelection);self.t.setEditTriggers(QAbstractItemView.NoEditTriggers);self.t.verticalHeader().setDefaultSectionSize(42);self.t.setMinimumHeight(150);l.addWidget(self.t)
        self.load()
    def load(self):
        rs=db.parties();self.t.setRowCount(len(rs))
        for r,x in enumerate(rs):
            self.t.setItem(r,0,QTableWidgetItem(x["name"]))
            self.t.setItem(r,1,QTableWidgetItem(x["gstin"]))
            self.t.setItem(r,2,QTableWidgetItem(x.get("manufacturer_code","") or ""))
            b=QPushButton("DELETE");b.setToolTip("DELETE PARTY");b.setFixedSize(92,32);b.setStyleSheet("font-weight:700;padding:4px 10px")
            b.clicked.connect(lambda _,name=x["name"]:self.delete_party(name))
            cell=QWidget();lay=QHBoxLayout(cell);lay.setContentsMargins(0,0,0,0);lay.setAlignment(Qt.AlignCenter);lay.addWidget(b);self.t.setCellWidget(r,3,cell)

    def delete_party(self,name):
        if not confirm_delete(
            self,
            "DELETE PARTY",
            f"DELETE “{name}” FROM PARTY MASTER?",
            "HISTORICAL PURCHASE BILLS WILL NOT BE DELETED."
        ):
            return
        try:
            db.delete_party(name)
            self.load()
            QMessageBox.information(self,"PARTIES","PARTY DELETED.")
        except Exception:
            db.log_error(traceback.format_exc())
            QMessageBox.critical(self,"PARTIES","COULD NOT DELETE PARTY. CHECK LOGS/ERROR.LOG.")
    def save(self):
        if not self.n.text().strip():return QMessageBox.warning(self,"PARTIES","PARTY NAME REQUIRED.")
        db.party(self.n.text().strip(),self.g.text().strip(),self.mcode.text().strip());self.load();self.n.clear();self.g.clear();self.mcode.clear();QMessageBox.information(self,"PARTIES","PARTY SAVED.")

class BillView(QWidget):
    def __init__(self,user,kind="PURCHASE"):
        super().__init__()
        self.user=user;self.kind=kind
        self.setWindowTitle("BILL VIEW")
        self.resize(1220,800)
        self.setStyleSheet("""
            QLineEdit,QComboBox{min-height:36px}
            QTableWidget{font-size:13px}
            QHeaderView::section{font-weight:700;padding:8px}
        """)
        l=QVBoxLayout(self)
        title=QLabel("BILL VIEW");title.setStyleSheet("font-size:22px;font-weight:700");l.addWidget(title)

        g=QGridLayout()
        self.kindbox=QComboBox();self.kindbox.addItems(["PURCHASE","SALE"]);self.kindbox.setCurrentText(kind)
        self.party=QLineEdit();self.party.setPlaceholderText("PARTY / CUSTOMER NAME")
        party_names=[x["name"] for x in db.parties()]
        self.party_completer=QCompleter(party_names,self.party)
        self.party_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.party_completer.setFilterMode(Qt.MatchContains)
        self.party_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.party.setCompleter(self.party_completer)
        self.invoice=QLineEdit();self.invoice.setPlaceholderText("INVOICE NUMBER")
        self.date=BillDateEdit();self.date.setPlaceholderText("BILL DATE  DDMMYY  •  e.g. 101226")
        view=QPushButton("VIEW BILL");view.setMinimumHeight(40)
        g.addWidget(QLabel("BILL TYPE"),0,0);g.addWidget(self.kindbox,0,1)
        g.addWidget(QLabel("PARTY / CUSTOMER"),0,2);g.addWidget(self.party,0,3)
        g.addWidget(QLabel("INVOICE NUMBER"),1,0);g.addWidget(self.invoice,1,1)
        g.addWidget(QLabel("BILL DATE"),1,2);g.addWidget(self.date,1,3)
        g.addWidget(view,0,4,2,1)
        l.addLayout(g)

        self.bill_info=QFrame()
        self.bill_info.setStyleSheet("QFrame{background:#191d24;border:1px solid #343943;border-radius:10px}")
        ig=QGridLayout(self.bill_info)
        self.info_party=QLabel("—");self.info_invoice=QLabel("—");self.info_date=QLabel("—")
        for q in (self.info_party,self.info_invoice,self.info_date):q.setStyleSheet("font-weight:700")
        ig.addWidget(QLabel("PARTY / CUSTOMER"),0,0);ig.addWidget(self.info_party,1,0)
        ig.addWidget(QLabel("INVOICE"),0,1);ig.addWidget(self.info_invoice,1,1)
        ig.addWidget(QLabel("DATE"),0,2);ig.addWidget(self.info_date,1,2)
        l.addWidget(self.bill_info)

        self.t=QTableWidget(0,8)
        self.t.setHorizontalHeaderLabels(["ITEM","HSN","DESIGN","QTY","RATE","GST %","GST AMOUNT","AMOUNT"])
        self.t.setAlternatingRowColors(True);self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.horizontalHeader().setStretchLastSection(True);self.t.verticalHeader().setDefaultSectionSize(38)
        l.addWidget(self.t,1)

        self.summary=QFrame()
        self.summary.setStyleSheet("QFrame{background:#191d24;border:1px solid #343943;border-radius:10px}")
        sg=QGridLayout(self.summary)
        self.gst5=QLabel("₹0.00");self.gst18=QLabel("₹0.00");self.totalgst=QLabel("₹0.00");self.grand=QLabel("₹0.00")
        self.grand.setStyleSheet("font-size:20px;font-weight:800;color:#d6bd86")
        for lab,w in [("GST @ 5%",self.gst5),("GST @ 18%",self.gst18),("TOTAL GST",self.totalgst),("GRAND TOTAL",self.grand)]:
            pass
        sg.addWidget(QLabel("GST @ 5%"),0,0);sg.addWidget(self.gst5,1,0)
        sg.addWidget(QLabel("GST @ 18%"),0,1);sg.addWidget(self.gst18,1,1)
        sg.addWidget(QLabel("TOTAL GST"),0,2);sg.addWidget(self.totalgst,1,2)
        q=QLabel("GRAND TOTAL");q.setStyleSheet("font-size:14px;font-weight:700");sg.addWidget(q,0,3);sg.addWidget(self.grand,1,3)
        l.addWidget(self.summary)

        self.kindbox.currentTextChanged.connect(self.clear_bill)
        view.clicked.connect(self.view_one)
        self._initial_popup_done=False

    def showEvent(self,event):
        super().showEvent(event)
        if not self._initial_popup_done:
            self._initial_popup_done=True
            self.choose_kind_popup()

    def choose_kind_popup(self):
        dlg=QDialog(self);dlg.setWindowTitle("SELECT BILL TYPE");dlg.setModal(True);dlg.setFixedSize(430,230)
        lay=QVBoxLayout(dlg);h=QLabel("SELECT BILL TYPE");h.setStyleSheet("font-size:19px;font-weight:700");lay.addWidget(h)
        sub=QLabel("Choose PURCHASE or SALE to continue.");sub.setStyleSheet("color:#aeb4bf");lay.addWidget(sub);lay.addStretch()
        row=QHBoxLayout();p=QPushButton("PURCHASE");s=QPushButton("SALE");p.setMinimumHeight(50);s.setMinimumHeight(50);row.addWidget(p);row.addWidget(s);lay.addLayout(row)
        p.clicked.connect(lambda:(self.kindbox.setCurrentText("PURCHASE"),dlg.accept()))
        s.clicked.connect(lambda:(self.kindbox.setCurrentText("SALE"),dlg.accept()))
        dlg.exec()

    def closeEvent(self,event):
        dash=getattr(self,"_dash",None)
        if dash is not None:
            dash.show();dash.raise_();dash.activateWindow()
        event.accept()

    def clear_bill(self):
        self.party.clear();self.invoice.clear();self.date.clear();self.t.setRowCount(0)
        self.info_party.setText("—");self.info_invoice.setText("—");self.info_date.setText("—")
        for x in (self.gst5,self.gst18,self.totalgst,self.grand):x.setText("₹0.00")

    def select_purchase_bill(self,bill_number):
        self.kindbox.setCurrentText("PURCHASE")
        rec=db.purchase_by_bill(str(bill_number))
        if not rec:return
        self.party.setText(str(rec.get("supplier_name") or ""))
        raw=str(rec.get("bill_date") or "")
        try:dt=datetime.strptime(raw,"%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:dt=raw
        self.date.setText(dt);self.invoice.setText(str(bill_number));self.view_one()

    def view_one(self):
        bill=self.invoice.text().strip()
        party=self.party.text().strip()
        date_text=self.date.text().replace("_","").strip()
        if not party:return QMessageBox.warning(self,"BILL VIEW","ENTER PARTY / CUSTOMER NAME.")
        if not bill:return QMessageBox.warning(self,"BILL VIEW","ENTER INVOICE NUMBER.")
        digits="".join(ch for ch in date_text if ch.isdigit())
        if len(digits) not in (6,8):
            return QMessageBox.warning(self,"BILL VIEW","ENTER BILL DATE AS 6 DIGITS. EXAMPLE: 101226 = 10-12-2026.")
        try:
            if len(digits)==6:
                dd,mm,yy=digits[:2],digits[2:4],digits[4:6]
                expected=datetime(2000+int(yy),int(mm),int(dd)).strftime("%Y-%m-%d")
            else:
                expected=datetime.strptime(digits,"%d%m%Y").strftime("%Y-%m-%d")
        except ValueError:
            return QMessageBox.warning(self,"BILL VIEW","INVALID BILL DATE.")
        rec=db.sale_by_bill(bill) if self.kindbox.currentText()=="SALE" else db.purchase_by_bill(bill)
        if not rec:return QMessageBox.warning(self,"BILL VIEW","BILL NOT FOUND.")
        rec_party=str(rec.get("customer_name") or rec.get("supplier_name") or "")
        if rec_party.lower()!=party.lower():return QMessageBox.warning(self,"BILL VIEW","PARTY / CUSTOMER DOES NOT MATCH THIS INVOICE.")
        if str(rec.get("bill_date") or "")!=expected:return QMessageBox.warning(self,"BILL VIEW","BILL DATE DOES NOT MATCH THIS INVOICE.")
        items=db.sale_items(rec["id"]) if self.kindbox.currentText()=="SALE" else db.purchase_items(rec["id"])
        self.t.setRowCount(len(items))
        gst5=gst18=totalgst=taxable_total=0.0
        for r,x in enumerate(items):
            qty=float(x.get("quantity") or 0);rate=float(x.get("rate") or 0);gst=float(x.get("gst_rate") or 0)
            taxable=rate*qty;gstamt=taxable*gst/100;amount=taxable+gstamt
            taxable_total+=taxable;totalgst+=gstamt
            if abs(gst-5)<.001:gst5+=gstamt
            elif abs(gst-18)<.001:gst18+=gstamt
            vals=[x.get("name",""),x.get("hsn_code",""),x.get("design_number",""),x.get("quantity",""),money(rate),f"{gst:g}%",money(gstamt),money(amount)]
            for c,v in enumerate(vals):self.t.setItem(r,c,QTableWidgetItem(str(v)))
        raw=str(rec.get("bill_date") or "")
        try:display=datetime.strptime(raw,"%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:display=raw
        self.info_party.setText(rec_party);self.info_invoice.setText(str(bill));self.info_date.setText(display)
        self.gst5.setText(money(gst5));self.gst18.setText(money(gst18));self.totalgst.setText(money(totalgst))
        self.grand.setText(money(float(rec.get("total_amount") or taxable_total+totalgst)))
        self.t.resizeColumnsToContents()
        for c,w in enumerate([260,95,120,70,115,75,120,135]):self.t.setColumnWidth(c,w)

class TemplateCanvasItem(QGraphicsTextItem):
    def __init__(self,key,text,rect,editor,font_size=10,bold=False,rotation=0):
        super().__init__(text)
        self.key=key; self.editor=editor
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setPos(rect.x(),rect.y()); self.setTextWidth(max(8,rect.width()))
        self.setRotation(rotation)
        f=QFont("Times New Roman",max(5,int(font_size))); f.setBold(bool(bold)); self.setFont(f)
        self.setDefaultTextColor(QColor("#111111"))
        self.setFlag(QGraphicsItem.ItemIsMovable,True)
        self.setFlag(QGraphicsItem.ItemIsSelectable,True)
    def mousePressEvent(self,e):
        self.editor.begin_edit_snapshot()
        super().mousePressEvent(e); self.editor.select_item(self)
    def mouseReleaseEvent(self,e):
        super().mouseReleaseEvent(e); self.editor.sync_fields()
    def mouseMoveEvent(self,e):
        super().mouseMoveEvent(e)
        if self.editor.snap.isChecked():
            g=1.0*self.editor.MM
            self.setPos(round(self.x()/g)*g,round(self.y()/g)*g)
        self.editor.sync_fields()

class TemplateEditor(QWidget):
    """Simple Canva-like editor for the 64 x 34 mm label.
    Presentation/template settings only; business data is never modified.
    """
    MM=6.0
    STICKER_W=64.0
    STICKER_H=34.0

    def __init__(self,user):
        super().__init__(); self.user=user; self.mode="BARCODE"; self.items={}; self._undo=[]; self._restoring=False
        self.setWindowTitle("RANISAA • TEMPLATE EDITOR • 64 × 34 MM")
        self.resize(1280,820); self.setMinimumSize(1050,700)
        root=QVBoxLayout(self); root.setContentsMargins(12,10,12,10)
        head=QHBoxLayout(); title=QLabel("TEMPLATE EDITOR"); title.setStyleSheet("font-size:22px;font-weight:700")
        head.addWidget(title); head.addStretch(); head.addWidget(QLabel("64 × 34 mm • A4 24 labels")); root.addLayout(head)
        tabs=QHBoxLayout(); self.btab=QPushButton("BARCODE"); self.billtab=QPushButton("BILL")
        self.btab.clicked.connect(lambda:self.switch_mode("BARCODE")); self.billtab.clicked.connect(lambda:self.switch_mode("BILL")); tabs.addWidget(self.btab);tabs.addWidget(self.billtab);tabs.addStretch();root.addLayout(tabs)
        body=QHBoxLayout(); root.addLayout(body,1)
        left=QFrame(); left.setFixedWidth(230); ll=QVBoxLayout(left)
        ll.addWidget(QLabel("ELEMENT")); self.field=QComboBox(); self.field.currentIndexChanged.connect(self.field_changed); ll.addWidget(self.field)
        self.visible=QCheckBox("Visible"); self.visible.stateChanged.connect(self.apply_props); ll.addWidget(self.visible)
        ll.addWidget(QLabel("QUICK ACTIONS")); ar=QHBoxLayout()
        self.rotate=QPushButton("↻ Rotate"); self.duplicate=QPushButton("Duplicate"); self.undo=QPushButton("↶ Undo")
        self.rotate.clicked.connect(self.rotate_item); self.duplicate.clicked.connect(self.duplicate_item); self.undo.clicked.connect(self.undo_action)
        ar.addWidget(self.rotate); ar.addWidget(self.duplicate); ll.addLayout(ar); ll.addWidget(self.undo)
        ll.addWidget(QLabel("TEXT")); tf=QFormLayout()
        self.text=QLineEdit(); self.text.editingFinished.connect(self.apply_text)
        self.size=QSpinBox(); self.size.setRange(5,40); self.size.setValue(10); self.size.valueChanged.connect(self.apply_props)
        self.bold=QCheckBox("Bold"); self.bold.stateChanged.connect(self.apply_props)
        self.italic=QCheckBox("Italic"); self.italic.stateChanged.connect(self.apply_props)
        tf.addRow("Text",self.text);tf.addRow("Size",self.size);tf.addRow("",self.bold);tf.addRow("",self.italic);ll.addLayout(tf)
        ll.addWidget(QLabel("ADD")); addrow=QHBoxLayout(); addtext=QPushButton("+ Text"); addbc=QPushButton("+ Barcode"); addbox=QPushButton("+ Box")
        addtext.clicked.connect(lambda:self.add_item("TEXT"));addbc.clicked.connect(lambda:self.add_item("BARCODE"));addbox.clicked.connect(lambda:self.add_item("BOX"))
        addrow.addWidget(addtext);addrow.addWidget(addbc);addrow.addWidget(addbox);ll.addLayout(addrow)
        dele=QPushButton("DELETE SELECTED"); dele.clicked.connect(self.delete_item);ll.addWidget(dele)
        self.save=QPushButton("SAVE TEMPLATE"); self.save.setStyleSheet("background:#16853a;color:white;font-weight:700");self.save.clicked.connect(self.save_template);ll.addWidget(self.save)
        preview=QPushButton("A4 PREVIEW • 24 LABELS");preview.clicked.connect(self.full_preview);ll.addWidget(preview)
        reset=QPushButton("RESET");reset.clicked.connect(self.reset_default);ll.addWidget(reset);ll.addStretch();body.addWidget(left)

        center=QFrame();cl=QVBoxLayout(center);tb=QHBoxLayout();self.snap=QCheckBox("Snap");self.snap.setChecked(True);tb.addWidget(QLabel("Drag elements like Canva"));tb.addWidget(self.snap);tb.addStretch()
        zoom=QComboBox();zoom.addItems(["100%","125%","150%","175%","200%"]);zoom.setCurrentText("150%");zoom.currentTextChanged.connect(self.set_zoom);tb.addWidget(QLabel("Zoom"));tb.addWidget(zoom);cl.addLayout(tb)
        self.scene=QGraphicsScene(self);self.scene.setSceneRect(0,0,self.STICKER_W*self.MM,self.STICKER_H*self.MM);self.view=QGraphicsView(self.scene);self.view.setRenderHint(self.view.renderHints());self.view.setStyleSheet("QGraphicsView{background:#d5d5d5;border:1px solid #aaa}");cl.addWidget(self.view,1);body.addWidget(center,1)
        right=QFrame();right.setFixedWidth(220);rl=QVBoxLayout(right);rl.addWidget(QLabel("LAYERS"));self.list=QListWidget();self.list.itemClicked.connect(self.list_select);rl.addWidget(self.list,1);z=QHBoxLayout();front=QPushButton("↑ Front");back=QPushButton("↓ Back");front.clicked.connect(lambda:self.nudge_z(1));back.clicked.connect(lambda:self.nudge_z(-1));z.addWidget(front);z.addWidget(back);rl.addLayout(z);body.addWidget(right)
        self.status=QLabel("Sticker: 64 × 34 mm | A4: 3 × 8 = 24");root.addWidget(self.status)
        self.switch_mode("BARCODE")

    def switch_mode(self,mode):
        self.mode=mode;self.btab.setStyleSheet("background:#1976d2;color:white;font-weight:700" if mode=="BARCODE" else "");self.billtab.setStyleSheet("background:#1976d2;color:white;font-weight:700" if mode=="BILL" else "");self.load_saved_or_default()

    def load_saved_or_default(self):
        self._undo=[];self.scene.clear();self.items={};self.list.clear();self.field.clear()
        loaded=False
        try:
            raw=db.setting("template_"+self.mode.lower(),"")
            data=json.loads(raw) if raw else {}
            if isinstance(data,dict) and data:
                for key,d in data.items():
                    if key=="__page__" or not isinstance(d,dict): continue
                    text=str(d.get("text",key));x=float(d.get("x",0));y=float(d.get("y",0));w=float(d.get("width",20));
                    fs=10;bold=False
                    qf=QFont()
                    if d.get("font"):
                        try:qf.fromString(str(d.get("font","")));fs=max(5,qf.pointSize());bold=qf.bold()
                        except Exception:pass
                    self._create(key,text,x,y,w,3,fs,bold)
                    it=self.items[key];it.setRotation(float(d.get("rotation",0) or 0));it.setVisible(bool(d.get("visible",True)))
                if self.items: loaded=True
        except Exception:
            loaded=False
        if not loaded:self.reset_default()
        else:
            self.field.addItems(self.items.keys());self.field.setCurrentIndex(0);self.fit_sticker()

    def default_fields(self):
        if self.mode=="BARCODE":
            # Exact source-style layout; design number is NOT printed beside STYLE NO.
            return [
                ("BRAND","RANISAA EXCLUSIVE",12,1.0,40,3.0,8,True),
                ("STYLE LABEL","STYLE NO.",5.0,7.0,20,2.5,5.0,False),
                ("STYLE VALUE","R59P13",8.0,9.1,18,3.0,7.5,True),
                ("COLOR","E3",49.0,7.2,7,3.0,7.5,True),
                ("BARCODE","|||||||||||||||||||||||||||||",19.0,8.0,26,6.0,8,False),
                ("BARCODE VALUE","RN582221",19.0,14.0,26,2.5,5.0,False),
                ("MRP","₹11388/-",19.0,17.8,26,4.0,9.5,True),
                ("NO EXCHANGE","NO EXCHANGE NO RETURN",16.0,23.0,32,2.2,5.2,True),
                ("NO GUARANTEE","NO GUARANTEE ON ANY COLOR AND FABRIC",8.0,25.3,48,2.2,4.4,True),
                ("ADDRESS PHONE","PATHANKOT, PUNJAB  |  9459672222",13.0,29.2,38,2.0,4.2,False),
                ("RLT-DATE","RLT-265",2.0,17.0,5,12,5.5,False),
                ("GST","G5T",55.0,17.0,6,4,7.0,False),
            ]
        return [
            ("BILL HEADER","RANISAA EXCLUSIVE",5,2,54,4,9,True),
            ("PARTY","PARTY / CUSTOMER",5,7,28,3,6,True),
            ("INVOICE","INVOICE",36,7,12,3,6,True),
            ("DATE","DATE",50,7,9,3,6,True),
            ("ITEMS","ITEM / HSN / DESIGN / QTY / RATE / GST / AMOUNT",5,12,54,8,5,False),
            ("GST SUMMARY","GST @ 5%     GST @ 18%     TOTAL GST",5,25,54,3,5,False),
            ("GRAND TOTAL","GRAND TOTAL  ₹0.00",36,29,23,3,7,True),
        ]

    def reset_default(self):
        self._undo=[];self.scene.clear();self.items={};self.list.clear();self.field.clear()
        for key,text,x,y,w,h,fs,bold in self.default_fields():
            self._create(key,text,x,y,w,h,fs,bold)
            if key in ("RLT-DATE","GST"):
                self.items[key].setRotation(90)
        self.field.addItems(self.items.keys());self.field.setCurrentIndex(0);self.fit_sticker()

    def _create(self,key,text,x,y,w,h,fs,bold=False):
        it=TemplateCanvasItem(key,text,QRectF(x*self.MM,y*self.MM,w*self.MM,h*self.MM),self,fs,bold);self.scene.addItem(it);self.items[key]=it;self.list.addItem(QListWidgetItem(key))

    def fit_sticker(self):self.view.fitInView(self.scene.sceneRect(),Qt.KeepAspectRatio)
    def set_zoom(self,v):self.view.resetTransform();self.view.scale(float(v[:-1])/100.0,float(v[:-1])/100.0)
    def begin_edit_snapshot(self):
        if not self._restoring:self._undo.append(self._snapshot());self._undo=self._undo[-30:]
    def _snapshot(self):
        return {k:{"x":it.x(),"y":it.y(),"w":it.textWidth(),"text":it.toPlainText(),"font":it.font().toString(),"rot":it.rotation(),"visible":it.isVisible()} for k,it in self.items.items()}
    def undo_action(self):
        if not self._undo:return
        st=self._undo.pop();self._restoring=True
        try:
            for k in list(self.items):
                if k not in st:self.scene.removeItem(self.items[k]);self.items.pop(k)
            for k,d in st.items():
                it=self.items.get(k)
                if not it:self._create(k,d["text"],d["x"]/self.MM,d["y"]/self.MM,max(8,d["w"])/self.MM,3,10,False);it=self.items[k]
                it.setPos(d["x"],d["y"]);it.setTextWidth(d["w"]);it.setPlainText(d["text"]);f=QFont();f.fromString(d["font"]);it.setFont(f);it.setRotation(d["rot"]);it.setVisible(d["visible"])
            self.list.clear();[self.list.addItem(QListWidgetItem(k)) for k in self.items];self.field.clear();self.field.addItems(self.items.keys())
        finally:self._restoring=False
        self.sync_fields()
    def current_item(self):return self.items.get(self.field.currentText())
    def select_item(self,it):
        self.scene.clearSelection();it.setSelected(True);self.field.blockSignals(True);self.field.setCurrentText(it.key);self.field.blockSignals(False);self.sync_fields()
    def list_select(self,item):
        it=self.items.get(item.text());
        if it:self.select_item(it)
    def field_changed(self):self.sync_fields()
    def sync_fields(self):
        it=self.current_item()
        if not it:return
        for q in (self.text,self.size,self.bold,self.italic,self.visible):q.blockSignals(True)
        self.text.setText(it.toPlainText());self.size.setValue(max(5,it.font().pointSize()));self.bold.setChecked(it.font().bold());self.italic.setChecked(it.font().italic());self.visible.setChecked(it.isVisible())
        for q in (self.text,self.size,self.bold,self.italic,self.visible):q.blockSignals(False)
    def apply_text(self):
        it=self.current_item()
        if not it or self._restoring:return
        self.begin_edit_snapshot();it.setPlainText(self.text.text());self.sync_fields()
    def apply_props(self):
        it=self.current_item()
        if not it or self._restoring:return
        self.begin_edit_snapshot();f=it.font();f.setPointSize(max(5,self.size.value()));f.setBold(self.bold.isChecked());f.setItalic(self.italic.isChecked());it.setFont(f);it.setVisible(self.visible.isChecked());self.sync_fields()
    def rotate_item(self):
        it=self.current_item()
        if it:self.begin_edit_snapshot();it.setRotation((int(it.rotation())+90)%360);self.sync_fields()
    def duplicate_item(self):
        it=self.current_item()
        if not it:return
        self.begin_edit_snapshot();n=f"{it.key} COPY";i=1
        while n in self.items:i+=1;n=f"{it.key} COPY {i}"
        self._create(n,it.toPlainText(),it.x()/self.MM+2,it.y()/self.MM+2,it.textWidth()/self.MM,3,it.font().pointSize(),it.font().bold());self.field.setCurrentText(n);self.list.setCurrentRow(self.list.count()-1)
    def add_item(self,kind):
        self.begin_edit_snapshot();n=1
        while f"CUSTOM {n}" in self.items:n+=1
        key=f"CUSTOM {n}";text="NEW TEXT" if kind=="TEXT" else ("||||||||||||||||||||" if kind=="BARCODE" else "BOX")
        self._create(key,text,8,12,24,3,6,kind=="BARCODE");self.field.setCurrentText(key);self.list.setCurrentRow(self.list.count()-1)
    def delete_item(self):
        it=self.current_item()
        if not it:return
        self.begin_edit_snapshot();self.scene.removeItem(it);self.items.pop(it.key,None);self.list.clear();[self.list.addItem(QListWidgetItem(k)) for k in self.items];self.field.clear();self.field.addItems(self.items.keys())
    def nudge_z(self,v):
        it=self.current_item()
        if it:self.begin_edit_snapshot();it.setZValue(it.zValue()+v)
    def save_template(self):
        data={k:{"x":round(it.x()/self.MM,2),"y":round(it.y()/self.MM,2),"width":round(it.textWidth()/self.MM,2),"text":it.toPlainText(),"rotation":int(it.rotation()),"visible":it.isVisible(),"font":it.font().toString()} for k,it in self.items.items()}
        data["__page__"]={"width_mm":64,"height_mm":34,"a4_columns":3,"a4_rows":8,"labels":24,"safe_side_mm":3}
        db.set_setting("template_"+self.mode.lower(),json.dumps(data));QMessageBox.information(self,"TEMPLATE SAVED","Template saved. Business data was not changed.")
    def _draw_one_preview(self,scene,x,y,scale=2.0):
        sc=scene
        # Sticker has no printed border. Preview only shows a faint safe-area guide.
        safe=3*scale
        guide_pen=QPen(QColor("#b8b8b8")); guide_pen.setStyle(Qt.DashLine); guide_pen.setWidth(1)
        sc.addRect(x+safe,y+safe,self.STICKER_W*scale-2*safe,self.STICKER_H*scale-2*safe,guide_pen,QBrush(Qt.NoBrush))
        for key,it in self.items.items():
            if not it.isVisible():continue
            txt=it.toPlainText();font=QFont(it.font());font.setPointSizeF(max(3,it.font().pointSizeF()*scale/3.0));
            q=sc.addText(txt,font);q.setPos(x+it.x()/self.MM*scale,y+it.y()/self.MM*scale);q.setRotation(it.rotation())
    def full_preview(self):
        dlg=QDialog(self);dlg.setWindowTitle("A4 PREVIEW • 24 LABELS • 64 × 34 MM");dlg.resize(850,1000);lay=QVBoxLayout(dlg);lay.addWidget(QLabel("A4 • 210 × 297 mm • 3 columns × 8 rows • sticker 64 × 34 mm • 3 mm safe side space"))
        sc=QGraphicsScene(dlg);a4s=2.0;sc.setSceneRect(0,0,210*a4s,297*a4s);sc.setBackgroundBrush(QBrush(QColor("#cfcfcf")))
        gapx=3*a4s;gap_y=2*a4s;sw=64*a4s;sh=34*a4s;left=(210*a4s-(3*sw+2*gapx))/2;top=7*a4s
        for r in range(8):
            for c in range(3):self._draw_one_preview(sc,left+c*(sw+gapx),top+r*(sh+gap_y),a4s)
        v=QGraphicsView(sc);v.fitInView(sc.sceneRect(),Qt.KeepAspectRatio);lay.addWidget(v,1);b=QPushButton("CLOSE");b.clicked.connect(dlg.accept);lay.addWidget(b);dlg.exec()
    def help(self):QMessageBox.information(self,"HOW TO USE","Click an element, drag it like Canva, edit its text/size on the left, rotate or duplicate it, and press Undo if needed. Sticker is exactly 64 × 34 mm. A4 preview shows 24 stickers with side-safe space. Save Template stores only presentation settings.")


class Settings(QWidget):
    def __init__(self,user):
        super().__init__();self.user=user;self.setWindowTitle("SETTINGS");self.resize(700,600);l=QVBoxLayout(self)
        l.addWidget(QLabel("APP AND DATA ARE SEPARATE. KEEP DATA/ WHEN UPDATING SOFTWARE."))
        sync=QPushButton("VERIFY & SYNC DATA");sync.clicked.connect(self.sync);l.addWidget(sync)
        repair=QPushButton("AUTO FIX / REPAIR ERRORS");repair.clicked.connect(self.auto_repair);l.addWidget(repair)
        backup=QPushButton("CREATE ENCRYPTED BACKUP");backup.clicked.connect(self.make_backup);l.addWidget(backup)
        restore=QPushButton("RESTORE BACKUP");restore.clicked.connect(self.restore);l.addWidget(restore)
        templ=QPushButton("TEMPLATE EDITOR • BARCODE / BILL");templ.clicked.connect(self.template);l.addWidget(templ)
        l.addWidget(QLabel("BILL TEMPLATE: OPTIONAL PNG/JPG BACKGROUND. A FINAL CUSTOM TEMPLATE CAN BE FITTED AFTER YOU PROVIDE THE DESIGN."))
    def sync(self):
        try:db.init_database();QMessageBox.information(self,"DATA SYNC","Database verified/migrated. Existing entries preserved.")
        except Exception:db.log_error(traceback.format_exc());QMessageBox.critical(self,"DATA SYNC","Sync failed; error logged.")
    def auto_repair(self):
        try:db.init_database();p=db.encrypted_backup();QMessageBox.information(self,"REPAIR COMPLETE",f"Database verified and safety backup created.\n{p}")
        except Exception:db.log_error(traceback.format_exc());QMessageBox.critical(self,"REPAIR","Repair failed; error logged.")
    def make_backup(self):QMessageBox.information(self,"BACKUP",str(db.encrypted_backup()))
    def restore(self):
        p=QFileDialog.getOpenFileName(self,"Select encrypted backup",str(db.BACKUP_DIR),"Encrypted backup (*.enc)")[0]
        if p and db.restore(p):QMessageBox.information(self,"RESTORE","Backup restored safely. Restart ERP.")
        elif p:QMessageBox.critical(self,"RESTORE","Restore failed.")
    def template(self):
        w=TemplateEditor(self.user);w.show();self._template_window=w


class Profile(QWidget):
    def __init__(self,user):
        super().__init__();self.user=user;self.setWindowTitle("PROFILE");l=QFormLayout(self)
        self.uid=QLineEdit(user["username"]);self.uid.setReadOnly(True);self.new=QLineEdit();self.new.setEchoMode(QLineEdit.Password);save=QPushButton("CHANGE PASSWORD");save.clicked.connect(self.change)
        l.addRow("User ID",self.uid);l.addRow("New Password",self.new);l.addRow(save)
    def change(self):
        p=self.new.text()
        if len(p)<4:return QMessageBox.warning(self,"PROFILE","Password must be at least 4 characters.")
        with db.tx() as c:c.execute("UPDATE users SET password_hash=? WHERE id=?",(db.h(p),self.user["id"]))
        QMessageBox.information(self,"PROFILE","Password changed.")

class Permissions(QWidget):
    def __init__(self,user):
        super().__init__();self.user=user;self.setWindowTitle("STAFF PERMISSIONS & USER LOGIN");self.resize(800,750);l=QVBoxLayout(self)
        l.addWidget(QLabel("STAFF PERMISSIONS"))
        self.c={};p=db.perms("staff")
        for k,label in MODULES.items():
            if k in ("billview",): continue
            c=QCheckBox(label);c.setChecked(p.get(k,False));self.c[k]=c;l.addWidget(c)
        save=QPushButton("SAVE STAFF PERMISSIONS");save.clicked.connect(self.save);l.addWidget(save)
        l.addWidget(QLabel("CHANGE STAFF / USER LOGIN"))
        self.users=QComboBox()
        self.user_map=[]
        for x in db.users_list():self.user_map.append(x);self.users.addItem(f'{x["username"]} • {x["role"]} • {x["full_name"]}',x["id"])
        l.addWidget(self.users)
        self.newid=QLineEdit();self.newid.setPlaceholderText("NEW USER ID / USERNAME");self.passw=QLineEdit();self.passw.setPlaceholderText("NEW PASSWORD");self.passw.setEchoMode(QLineEdit.Password);self.full=QLineEdit();self.full.setPlaceholderText("FULL NAME")
        l.addWidget(self.newid);l.addWidget(self.passw);l.addWidget(self.full)
        ch=QPushButton("CHANGE USER ID / PASSWORD");ch.clicked.connect(self.change_login);l.addWidget(ch)
    def save(self):
        for k,c in self.c.items():db.set_perm("staff",k,c.isChecked())
        QMessageBox.information(self,"SAVED","Staff permissions saved.")
    def change_login(self):
        uid=self.users.currentData()
        if not uid or not self.newid.text().strip() or not self.passw.text():return QMessageBox.warning(self,"LOGIN","User ID and new password are required.")
        try:db.update_user_credentials(uid,self.newid.text(),self.passw.text(),self.full.text() or None);QMessageBox.information(self,"LOGIN","User ID/password changed. Restart/login again.")
        except Exception as e:db.log_error(traceback.format_exc());QMessageBox.critical(self,"LOGIN","Could not change credentials. Check logs/error.log.")

def main():
    db.init_database();db.auto_backup()
    a=QApplication(sys.argv);a.setStyleSheet(STYLE);font=a.font();font.setPointSize(10);a.setFont(font);w=Login();w.show();return a.exec()
if __name__=="__main__":
    try:sys.exit(main())
    except Exception:
        db.log_error(traceback.format_exc());QMessageBox.critical(None,"RANISAA ERP","Error logged. Run repair.py.")
