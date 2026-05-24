"""
Triton Wealth Management - Investment Portfolio Report Generator
Equitable Life Segregated Funds - Chinese Client Report
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas

# ── Brand colors ──────────────────────────────────────────────
NAVY       = colors.HexColor('#1C2B4A')
GOLD       = colors.HexColor('#C9A256')
GOLD_LIGHT = colors.HexColor('#E8D5A3')
GOLD_DARK  = colors.HexColor('#9A7B2E')
WHITE      = colors.white
LIGHT_GRAY = colors.HexColor('#F5F5F5')
MID_GRAY   = colors.HexColor('#E0E0E0')
DARK_GRAY  = colors.HexColor('#4A4A4A')
RED_ACCENT = colors.HexColor('#C0392B')
GREEN_ACCENT = colors.HexColor('#27AE60')
BLUE_ACCENT  = colors.HexColor('#2980B9')

# ── Register Chinese fonts ─────────────────────────────────────
FONT_DIR = r'C:\Windows\Fonts'
font_pairs = [
    ('MicrosoftYaHei', 'msyh.ttc'),
    ('MicrosoftYaHei', 'msyh.ttf'),
    ('SimHei',         'simhei.ttf'),
    ('SimSun',         'simsun.ttc'),
]
CN_FONT = None
for name, fname in font_pairs:
    path = os.path.join(FONT_DIR, fname)
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            CN_FONT = name
            print(f"Registered font: {name} from {path}")
            break
        except Exception as e:
            print(f"  Failed {name}: {e}")

# Bold variant
CN_BOLD = CN_FONT
bold_pairs = [
    ('MicrosoftYaHeiBold', 'msyhbd.ttc'),
    ('MicrosoftYaHeiBold', 'msyhbd.ttf'),
]
for name, fname in bold_pairs:
    path = os.path.join(FONT_DIR, fname)
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            CN_BOLD = name
            print(f"Registered bold font: {name}")
            break
        except Exception as e:
            print(f"  Failed bold {name}: {e}")

if CN_FONT is None:
    print("ERROR: No Chinese font found. Please install Microsoft YaHei or SimHei.")
    sys.exit(1)

# ── Output path ────────────────────────────────────────────────
OUTPUT = r'C:\Users\Admin\Desktop\Fund proposal\Triton_Wealth_Investment_Portfolio_2025.pdf'
LOGO   = r'C:\Users\Admin\Desktop\Triton investor\LOGO PNG 竖版.png'

# ── Styles ─────────────────────────────────────────────────────
def make_styles():
    s = {}

    s['cover_title'] = ParagraphStyle('cover_title',
        fontName=CN_BOLD, fontSize=28, leading=36,
        alignment=TA_CENTER, textColor=WHITE, spaceAfter=8)

    s['cover_sub'] = ParagraphStyle('cover_sub',
        fontName=CN_FONT, fontSize=14, leading=20,
        alignment=TA_CENTER, textColor=GOLD_LIGHT, spaceAfter=6)

    s['cover_date'] = ParagraphStyle('cover_date',
        fontName=CN_FONT, fontSize=11, leading=16,
        alignment=TA_CENTER, textColor=GOLD_LIGHT)

    s['section_title'] = ParagraphStyle('section_title',
        fontName=CN_BOLD, fontSize=16, leading=22,
        textColor=NAVY, spaceBefore=14, spaceAfter=8,
        borderPad=4)

    s['sub_title'] = ParagraphStyle('sub_title',
        fontName=CN_BOLD, fontSize=13, leading=18,
        textColor=GOLD_DARK, spaceBefore=10, spaceAfter=6)

    s['body'] = ParagraphStyle('body',
        fontName=CN_FONT, fontSize=10, leading=16,
        textColor=DARK_GRAY, spaceAfter=5, alignment=TA_JUSTIFY)

    s['body_bold'] = ParagraphStyle('body_bold',
        fontName=CN_BOLD, fontSize=10, leading=16,
        textColor=DARK_GRAY, spaceAfter=5)

    s['table_header'] = ParagraphStyle('table_header',
        fontName=CN_BOLD, fontSize=9, leading=13,
        textColor=WHITE, alignment=TA_CENTER)

    s['table_cell'] = ParagraphStyle('table_cell',
        fontName=CN_FONT, fontSize=9, leading=13,
        textColor=DARK_GRAY, alignment=TA_CENTER)

    s['table_cell_left'] = ParagraphStyle('table_cell_left',
        fontName=CN_FONT, fontSize=9, leading=13,
        textColor=DARK_GRAY, alignment=TA_LEFT)

    s['table_cell_bold'] = ParagraphStyle('table_cell_bold',
        fontName=CN_BOLD, fontSize=9, leading=13,
        textColor=NAVY, alignment=TA_CENTER)

    s['highlight'] = ParagraphStyle('highlight',
        fontName=CN_BOLD, fontSize=11, leading=16,
        textColor=GOLD_DARK, spaceAfter=4)

    s['note'] = ParagraphStyle('note',
        fontName=CN_FONT, fontSize=8, leading=12,
        textColor=colors.HexColor('#888888'), spaceAfter=4)

    s['green'] = ParagraphStyle('green',
        fontName=CN_BOLD, fontSize=9, leading=13,
        textColor=GREEN_ACCENT, alignment=TA_CENTER)

    s['red'] = ParagraphStyle('red',
        fontName=CN_BOLD, fontSize=9, leading=13,
        textColor=RED_ACCENT, alignment=TA_CENTER)

    return s

ST = make_styles()

# ── Helper: gold divider ───────────────────────────────────────
def gold_line():
    return HRFlowable(width='100%', thickness=1.5, color=GOLD, spaceAfter=8, spaceBefore=4)

def thin_line():
    return HRFlowable(width='100%', thickness=0.5, color=MID_GRAY, spaceAfter=6, spaceBefore=4)

def P(text, style='body'):
    return Paragraph(text, ST[style])

def sp(h=6):
    return Spacer(1, h)

# ── Section header block ───────────────────────────────────────
def section_header(title, subtitle=''):
    items = [
        sp(4),
        gold_line(),
        P(title, 'section_title'),
    ]
    if subtitle:
        items.append(P(subtitle, 'body'))
    items.append(sp(4))
    return items

# ── Portfolio color by risk ────────────────────────────────────
RISK_COLORS = {
    'low':  colors.HexColor('#2980B9'),
    'mid':  colors.HexColor('#27AE60'),
    'high': colors.HexColor('#E67E22'),
}

# ── Table style helper ─────────────────────────────────────────
def base_table_style(header_color=NAVY):
    return TableStyle([
        ('BACKGROUND', (0,0), (-1,0), header_color),
        ('TEXTCOLOR',  (0,0), (-1,0), WHITE),
        ('FONTNAME',   (0,0), (-1,0), CN_BOLD),
        ('FONTSIZE',   (0,0), (-1,0), 9),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ('GRID',       (0,0), (-1,-1), 0.5, MID_GRAY),
        ('LINEBELOW',  (0,0), (-1,0), 1.5, GOLD),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
    ])

# ══════════════════════════════════════════════════════════════
#  COVER PAGE  (drawn on canvas)
# ══════════════════════════════════════════════════════════════
class CoverPage(Flowable):
    def __init__(self, logo_path):
        Flowable.__init__(self)
        self.logo_path = logo_path
        self.width, self.height = A4

    def draw(self):
        c = self.canv
        W, H = self.width, self.height

        # Navy background
        c.setFillColor(NAVY)
        c.rect(0, 0, W, H, fill=1, stroke=0)

        # Gold top stripe
        c.setFillColor(GOLD)
        c.rect(0, H - 12*mm, W, 12*mm, fill=1, stroke=0)

        # Gold bottom stripe
        c.rect(0, 0, W, 8*mm, fill=1, stroke=0)

        # Decorative side gold bar
        c.setFillColor(GOLD_DARK)
        c.rect(0, 0, 6*mm, H, fill=1, stroke=0)

        # Logo (white background patch)
        logo_w = 70*mm
        logo_h = 70*mm
        logo_x = (W - logo_w) / 2
        logo_y = H - 60*mm - logo_h
        if os.path.exists(self.logo_path):
            c.setFillColor(WHITE)
            c.roundRect(logo_x - 8*mm, logo_y - 5*mm,
                        logo_w + 16*mm, logo_h + 10*mm,
                        radius=6*mm, fill=1, stroke=0)
            c.drawImage(self.logo_path, logo_x, logo_y,
                        width=logo_w, height=logo_h,
                        preserveAspectRatio=True, anchor='c',
                        mask='auto')

        # Titles
        c.setFillColor(WHITE)
        c.setFont(CN_BOLD, 24)
        c.drawCentredString(W/2, logo_y - 22*mm,
                            '投资组合建议报告')

        c.setFillColor(GOLD_LIGHT)
        c.setFont(CN_FONT, 13)
        c.drawCentredString(W/2, logo_y - 33*mm,
                            'Equitable Life 保险分红基金 · 定制投资方案')

        # Divider
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.5)
        c.line(W*0.2, logo_y - 40*mm, W*0.8, logo_y - 40*mm)

        # Key info box
        box_y = logo_y - 95*mm
        c.setFillColor(colors.HexColor('#243660'))
        c.roundRect(20*mm, box_y, W - 40*mm, 48*mm,
                    radius=4*mm, fill=1, stroke=0)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1)
        c.roundRect(20*mm, box_y, W - 40*mm, 48*mm,
                    radius=4*mm, fill=0, stroke=1)

        items = [
            ('参考本金', '$1,000,000 CAD'),
            ('风险等级', '中低  |  中等  |  中高'),
            ('产品类型', '分离账户基金（Segregated Fund）'),
            ('报告日期', '2025年5月'),
        ]
        c.setFont(CN_FONT, 10)
        c.setFillColor(GOLD_LIGHT)
        row_h = 10*mm
        for i, (label, value) in enumerate(items):
            y = box_y + 38*mm - i * row_h
            c.setFillColor(GOLD)
            c.drawString(28*mm, y, label + '：')
            c.setFillColor(WHITE)
            c.drawString(65*mm, y, value)

        # Footer
        c.setFillColor(GOLD_LIGHT)
        c.setFont(CN_FONT, 8)
        c.drawCentredString(W/2, 12*mm,
            'Triton Wealth Management Corporation  |  富瑞财富管理')

    def wrap(self, availW, availH):
        return (self.width, self.height)


# ══════════════════════════════════════════════════════════════
#  CONTENT BUILDER
# ══════════════════════════════════════════════════════════════
def build_story():
    story = []

    # Page 1 is the cover (drawn via onFirstPage callback) — advance past it
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════
    # 1. 产品简介
    # ═══════════════════════════════════════════════════════
    story += section_header('一、分离账户基金（Segregated Fund）简介',
                            'Equitable Life 保险公司提供的专属保险投资产品')

    story.append(P(
        'Equitable Life（公平人寿）成立于1920年，是加拿大历史悠久的互助型人寿保险公司之一，'
        '无需向股东分红，全部盈余用于回报保单持有人。其分离账户基金（Segregated Fund）结合了'
        '投资基金的增长潜力与保险合同的独特保障，是理财规划中兼顾增值与保护的优质工具。'
    ))
    story.append(sp(4))

    # Key advantages table
    adv_data = [
        [P('核心优势', 'table_header'), P('说明', 'table_header')],
        [P('到期保证（Maturity Guarantee）', 'table_cell_left'),
         P('持有至到期（通常10年），可保证本金的75%–100%', 'table_cell_left')],
        [P('身故保证（Death Benefit）', 'table_cell_left'),
         P('身故时受益人可获得保证金额（75%–100%），快速免遗产认证', 'table_cell_left')],
        [P('债权人保护（Creditor Protection）', 'table_cell_left'),
         P('指定直系亲属为受益人时，资产可受债权人追索保护', 'table_cell_left')],
        [P('绕过遗嘱认证（Bypass Probate）', 'table_cell_left'),
         P('资产直接传承受益人，无需等待繁琐的遗产认证程序，节省时间与费用', 'table_cell_left')],
        [P('私密性强', 'table_cell_left'),
         P('作为保险合同，不进入公开遗嘱记录，资产传承更私密', 'table_cell_left')],
        [P('投资选择丰富', 'table_cell_left'),
         P('覆盖货币市场、固定收益、平衡型、股票型等多种基金，满足不同风险偏好', 'table_cell_left')],
    ]
    adv_t = Table(adv_data, colWidths=[65*mm, 105*mm])
    adv_t.setStyle(base_table_style())
    adv_t.setStyle(TableStyle([
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
    ]))
    story.append(adv_t)
    story.append(sp(8))

    # ═══════════════════════════════════════════════════════
    # 2. 三种风险组合
    # ═══════════════════════════════════════════════════════
    story += section_header('二、三大风险等级投资组合方案',
                            '根据客户风险承受能力，量身定制的分离账户基金组合')

    story.append(P(
        '以下三个组合均基于Equitable Life现有分离账户基金精选构建，'
        '历史回报数据截至2025年4月30日，以净值回报率（扣除MER管理费）为准。'
        '过去表现不代表未来回报，投资前请充分了解产品风险。'
    ))
    story.append(sp(6))

    # ── 2.1 中低风险 ─────────────────────────────────────
    story.append(KeepTogether([
        P('▌ 组合一：中低风险组合（Conservative Portfolio）', 'sub_title'),
        P('适合人群：注重资产保值、风险承受能力较低、希望稳健增长的投资者。', 'body'),
        P('资产配置目标：约 25–35% 股票 / 65–75% 固定收益', 'body'),
        sp(4),
    ]))

    p1_data = [
        [P('基金名称', 'table_header'),
         P('股票占比', 'table_header'),
         P('固收占比', 'table_header'),
         P('MER', 'table_header'),
         P('配置比例', 'table_header'),
         P('1年回报', 'table_header'),
         P('3年回报', 'table_header'),
         P('5年回报', 'table_header')],
        [P('Franklin Conservative Income ETF', 'table_cell_left'),
         P('27.8%', 'table_cell'), P('72.2%', 'table_cell'), P('2.47%', 'table_cell'),
         P('35%', 'table_cell_bold'),
         P('8.3%', 'green'), P('5.7%', 'green'), P('1.9%', 'green')],
        [P('Canoe Enhanced Income', 'table_cell_left'),
         P('24.7%', 'table_cell'), P('72.6%', 'table_cell'), P('2.58%', 'table_cell'),
         P('35%', 'table_cell_bold'),
         P('6.5%', 'green'), P('5.6%', 'green'), P('3.5%', 'green')],
        [P('Quotential Balanced Income', 'table_cell_left'),
         P('45.1%', 'table_cell'), P('54.9%', 'table_cell'), P('2.84%', 'table_cell'),
         P('20%', 'table_cell_bold'),
         P('10.3%', 'green'), P('6.8%', 'green'), P('3.1%', 'green')],
        [P('Equitable Money Market', 'table_cell_left'),
         P('0.0%', 'table_cell'), P('97.7%', 'table_cell'), P('1.34%', 'table_cell'),
         P('10%', 'table_cell_bold'),
         P('1.7%', 'table_cell'), P('2.9%', 'table_cell'), P('2.1%', 'table_cell')],
        [P('【组合加权平均】', 'table_cell_bold'),
         P('~29%', 'table_cell_bold'), P('~71%', 'table_cell_bold'), P('—', 'table_cell'),
         P('100%', 'table_cell_bold'),
         P('7.1%', 'green'), P('5.5%', 'green'), P('2.7%', 'green')],
    ]
    p1_t = Table(p1_data, colWidths=[52*mm, 16*mm, 16*mm, 14*mm, 18*mm, 18*mm, 18*mm, 18*mm])
    p1_t.setStyle(base_table_style(colors.HexColor('#2980B9')))
    p1_t.setStyle(TableStyle([
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#D6EAF8')),
        ('FONTNAME', (0,-1), (-1,-1), CN_BOLD),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#2980B9')),
    ]))
    story.append(p1_t)
    story.append(sp(10))

    # ── 2.2 中等风险 ─────────────────────────────────────
    story.append(KeepTogether([
        P('▌ 组合二：中等风险组合（Balanced Portfolio）', 'sub_title'),
        P('适合人群：希望在稳健中寻求合理增长，接受一定市场波动的投资者。', 'body'),
        P('资产配置目标：约 55–65% 股票 / 35–45% 固定收益', 'body'),
        sp(4),
    ]))

    p2_data = [
        [P('基金名称', 'table_header'),
         P('股票占比', 'table_header'),
         P('固收占比', 'table_header'),
         P('MER', 'table_header'),
         P('配置比例', 'table_header'),
         P('1年回报', 'table_header'),
         P('3年回报', 'table_header'),
         P('5年回报', 'table_header')],
        [P('Equitable Balanced', 'table_cell_left'),
         P('54.4%', 'table_cell'), P('45.1%', 'table_cell'), P('2.45%', 'table_cell'),
         P('40%', 'table_cell_bold'),
         P('14.9%', 'green'), P('9.2%', 'green'), P('5.3%', 'green')],
        [P('Franklin Core ETF Portfolio', 'table_cell_left'),
         P('61.8%', 'table_cell'), P('38.2%', 'table_cell'), P('2.49%', 'table_cell'),
         P('35%', 'table_cell_bold'),
         P('17.2%', 'green'), P('10.5%', 'green'), P('5.5%', 'green')],
        [P('Quotential Balanced Growth', 'table_cell_left'),
         P('64.0%', 'table_cell'), P('36.0%', 'table_cell'), P('2.91%', 'table_cell'),
         P('25%', 'table_cell_bold'),
         P('15.7%', 'green'), P('9.8%', 'green'), P('5.4%', 'green')],
        [P('【组合加权平均】', 'table_cell_bold'),
         P('~59%', 'table_cell_bold'), P('~41%', 'table_cell_bold'), P('—', 'table_cell'),
         P('100%', 'table_cell_bold'),
         P('15.9%', 'green'), P('9.8%', 'green'), P('5.4%', 'green')],
    ]
    p2_t = Table(p2_data, colWidths=[52*mm, 16*mm, 16*mm, 14*mm, 18*mm, 18*mm, 18*mm, 18*mm])
    p2_t.setStyle(base_table_style(colors.HexColor('#27AE60')))
    p2_t.setStyle(TableStyle([
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#D5F5E3')),
        ('FONTNAME', (0,-1), (-1,-1), CN_BOLD),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#27AE60')),
    ]))
    story.append(p2_t)
    story.append(sp(10))

    # ── 2.3 中高风险 ─────────────────────────────────────
    story.append(KeepTogether([
        P('▌ 组合三：中高风险组合（Growth Portfolio）', 'sub_title'),
        P('适合人群：追求资产较快增长，能承受较大市场波动，投资周期5年以上的投资者。', 'body'),
        P('资产配置目标：约 75–85% 股票 / 15–25% 固定收益', 'body'),
        sp(4),
    ]))

    p3_data = [
        [P('基金名称', 'table_header'),
         P('股票占比', 'table_header'),
         P('固收占比', 'table_header'),
         P('MER', 'table_header'),
         P('配置比例', 'table_header'),
         P('1年回报', 'table_header'),
         P('3年回报', 'table_header'),
         P('5年回报', 'table_header')],
        [P('Franklin Growth ETF Portfolio', 'table_cell_left'),
         P('80.4%', 'table_cell'), P('17.4%', 'table_cell'), P('2.40%', 'table_cell'),
         P('40%', 'table_cell_bold'),
         P('23.6%', 'green'), P('13.9%', 'green'), P('8.0%', 'green')],
        [P('Quotential Growth Portfolio', 'table_cell_left'),
         P('82.9%', 'table_cell'), P('17.1%', 'table_cell'), P('2.96%', 'table_cell'),
         P('35%', 'table_cell_bold'),
         P('21.1%', 'green'), P('12.7%', 'green'), P('7.7%', 'green')],
        [P('Canoe Asset Allocation Portfolio', 'table_cell_left'),
         P('71.5%', 'table_cell'), P('28.5%', 'table_cell'), P('2.63%', 'table_cell'),
         P('25%', 'table_cell_bold'),
         P('15.3%', 'green'), P('10.7%', 'green'), P('9.8%', 'green')],
        [P('【组合加权平均】', 'table_cell_bold'),
         P('~79%', 'table_cell_bold'), P('~21%', 'table_cell_bold'), P('—', 'table_cell'),
         P('100%', 'table_cell_bold'),
         P('20.6%', 'green'), P('12.6%', 'green'), P('8.4%', 'green')],
    ]
    p3_t = Table(p3_data, colWidths=[52*mm, 16*mm, 16*mm, 14*mm, 18*mm, 18*mm, 18*mm, 18*mm])
    p3_t.setStyle(base_table_style(colors.HexColor('#E67E22')))
    p3_t.setStyle(TableStyle([
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FDEBD0')),
        ('FONTNAME', (0,-1), (-1,-1), CN_BOLD),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#E67E22')),
    ]))
    story.append(p3_t)
    story.append(sp(6))
    story.append(P(
        '※ 以上历史回报数据来源：Equitable Life FundData（截至2025年4月30日），'
        '已扣除管理费用（MER），均为年化回报率。', 'note'))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════
    # 3. 历史回报汇总对比
    # ═══════════════════════════════════════════════════════
    story += section_header('三、三大组合历史回报汇总对比',
                            '数据来源：Equitable Life FundData，截至2025年4月30日')

    comp_data = [
        [P('组合', 'table_header'),
         P('风险等级', 'table_header'),
         P('股/债比例', 'table_header'),
         P('近1年回报', 'table_header'),
         P('近3年（年化）', 'table_header'),
         P('近5年（年化）', 'table_header'),
         P('预期年化回报\n（保守估算）', 'table_header')],
        [P('中低风险组合', 'table_cell_bold'),
         P('★★☆☆☆', 'table_cell'),
         P('29% / 71%', 'table_cell'),
         P('7.1%', 'green'), P('5.5%', 'green'), P('2.7%', 'green'),
         P('4%–6%', 'table_cell_bold')],
        [P('中等风险组合', 'table_cell_bold'),
         P('★★★☆☆', 'table_cell'),
         P('59% / 41%', 'table_cell'),
         P('15.9%', 'green'), P('9.8%', 'green'), P('5.4%', 'green'),
         P('7%–9%', 'table_cell_bold')],
        [P('中高风险组合', 'table_cell_bold'),
         P('★★★★☆', 'table_cell'),
         P('79% / 21%', 'table_cell'),
         P('20.6%', 'green'), P('12.6%', 'green'), P('8.4%', 'green'),
         P('9%–12%', 'table_cell_bold')],
    ]
    comp_t = Table(comp_data, colWidths=[35*mm, 22*mm, 22*mm, 22*mm, 25*mm, 25*mm, 29*mm])
    comp_t.setStyle(base_table_style())
    comp_t.setStyle(TableStyle([
        ('BACKGROUND', (0,1), (0,1), colors.HexColor('#EBF5FB')),
        ('BACKGROUND', (0,2), (0,2), colors.HexColor('#EAFAF1')),
        ('BACKGROUND', (0,3), (0,3), colors.HexColor('#FEF9E7')),
    ]))
    story.append(comp_t)
    story.append(sp(10))

    # ═══════════════════════════════════════════════════════
    # 4. $100万本金预测回报
    # ═══════════════════════════════════════════════════════
    story += section_header('四、$1,000,000 本金投资预期回报测算',
                            '基于历史平均回报的保守估算，不构成任何回报保证')

    story.append(P(
        '以下测算以 $1,000,000 CAD 作为初始本金，按各组合保守预期年化回报率进行复利增长计算。'
        '中低风险取5%、中等风险取8%、中高风险取10%作为参考年化回报率。'
    ))
    story.append(sp(6))

    def fmt(n):
        return f'${n:,.0f}'

    def grow(principal, rate, years):
        return principal * ((1 + rate) ** years)

    p = 1_000_000
    rows_proj = [
        [P('投资年限', 'table_header'),
         P('中低风险组合\n（5%/年）', 'table_header'),
         P('较本金增加', 'table_header'),
         P('中等风险组合\n（8%/年）', 'table_header'),
         P('较本金增加', 'table_header'),
         P('中高风险组合\n（10%/年）', 'table_header'),
         P('较本金增加', 'table_header')],
    ]
    for yr, r1, r2, r3 in [(1,0.05,0.08,0.10),(3,0.05,0.08,0.10),
                            (5,0.05,0.08,0.10),(10,0.05,0.08,0.10),(20,0.05,0.08,0.10)]:
        v1 = grow(p, r1, yr); v2 = grow(p, r2, yr); v3 = grow(p, r3, yr)
        rows_proj.append([
            P(f'{yr} 年', 'table_cell_bold'),
            P(fmt(v1), 'table_cell'),
            P(f'+{fmt(v1-p)}', 'green'),
            P(fmt(v2), 'table_cell'),
            P(f'+{fmt(v2-p)}', 'green'),
            P(fmt(v3), 'table_cell'),
            P(f'+{fmt(v3-p)}', 'green'),
        ])

    proj_t = Table(rows_proj, colWidths=[18*mm, 28*mm, 22*mm, 28*mm, 22*mm, 28*mm, 22*mm])
    proj_t.setStyle(base_table_style())
    proj_t.setStyle(TableStyle([
        ('BACKGROUND', (1,0), (2,0), colors.HexColor('#2980B9')),
        ('BACKGROUND', (3,0), (4,0), colors.HexColor('#27AE60')),
        ('BACKGROUND', (5,0), (6,0), colors.HexColor('#E67E22')),
        ('SPAN', (0,0), (0,0)),
    ]))
    story.append(proj_t)
    story.append(sp(6))
    story.append(P(
        '※ 以上数据为复利计算的理论测算值，实际投资收益受市场影响，可能高于或低于预期。'
        '本表格仅供参考，不构成任何形式的回报保证或投资建议。', 'note'))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════
    # 5. 与银行GIC对比
    # ═══════════════════════════════════════════════════════
    story += section_header('五、分离账户基金 vs 银行GIC 综合对比',
                            '从回报率、税务效率、灵活性及额外保障四个维度全面分析')

    story.append(P(
        '银行定期存款（GIC）是许多保守投资者的传统选择，但在当前利率环境下，'
        '分离账户基金在回报潜力、税务优化及资产保护方面均具有明显优势。以下为详细对比分析。'
    ))
    story.append(sp(8))

    # ── 5.1 回报率对比 ────────────────────────────────────
    story.append(P('▌ 5.1 回报率对比（以 $1,000,000 本金为例）', 'sub_title'))

    ret_data = [
        [P('产品', 'table_header'),
         P('参考年化利率/回报', 'table_header'),
         P('1年税前收益', 'table_header'),
         P('3年税前总收益', 'table_header'),
         P('5年税前总收益', 'table_header'),
         P('可赎回性', 'table_header')],
        [P('银行 GIC（1年期）', 'table_cell_left'),
         P('~3.5%', 'table_cell'),
         P('$35,000', 'table_cell'),
         P('$108,717', 'table_cell'),
         P('$187,686', 'table_cell'),
         P('到期才可赎回', 'table_cell')],
        [P('银行 GIC（3年期）', 'table_cell_left'),
         P('~3.3%', 'table_cell'),
         P('$33,000', 'table_cell'),
         P('$102,831', 'table_cell'),
         P('$179,074', 'table_cell'),
         P('锁定3年', 'table_cell')],
        [P('银行 GIC（5年期）', 'table_cell_left'),
         P('~3.0%', 'table_cell'),
         P('$30,000', 'table_cell'),
         P('$92,727', 'table_cell'),
         P('$159,274', 'table_cell'),
         P('锁定5年', 'table_cell')],
        [P('分离基金 - 中低风险', 'table_cell_left'),
         P('~5%（保守估算）', 'table_cell'),
         P('$50,000', 'green'),
         P('$157,625', 'green'),
         P('$276,282', 'green'),
         P('随时赎回', 'green')],
        [P('分离基金 - 中等风险', 'table_cell_left'),
         P('~8%（保守估算）', 'table_cell'),
         P('$80,000', 'green'),
         P('$259,712', 'green'),
         P('$469,328', 'green'),
         P('随时赎回', 'green')],
        [P('分离基金 - 中高风险', 'table_cell_left'),
         P('~10%（保守估算）', 'table_cell'),
         P('$100,000', 'green'),
         P('$331,000', 'green'),
         P('$610,510', 'green'),
         P('随时赎回', 'green')],
    ]
    ret_t = Table(ret_data, colWidths=[42*mm, 32*mm, 28*mm, 28*mm, 28*mm, 22*mm])
    ret_t.setStyle(base_table_style())
    ret_t.setStyle(TableStyle([
        ('BACKGROUND', (0,1), (-1,3), colors.HexColor('#FEF9E7')),
        ('BACKGROUND', (0,4), (-1,6), colors.HexColor('#EAFAF1')),
        ('TEXTCOLOR', (0,1), (0,3), colors.HexColor('#E74C3C')),
        ('FONTNAME', (0,1), (0,-1), CN_BOLD),
    ]))
    story.append(ret_t)
    story.append(sp(10))

    # ── 5.2 税务对比 ─────────────────────────────────────
    story.append(P('▌ 5.2 税务效率对比（以安省最高边际税率43.41%为例）', 'sub_title'))
    story.append(P(
        'GIC的利息收入属于普通收入（Interest Income），按全额100%纳入应税收入；'
        '而分离账户基金的收益主要以资本利得（Capital Gain）形式体现，'
        '资本利得仅50%纳入应税收入，税务效率显著更优。'
    ))
    story.append(sp(6))

    tax_data = [
        [P('项目', 'table_header'),
         P('银行 GIC\n（年化3.5%）', 'table_header'),
         P('分离基金 - 中低\n（年化5%）', 'table_header'),
         P('分离基金 - 中等\n（年化8%）', 'table_header'),
         P('分离基金 - 中高\n（年化10%）', 'table_header')],
        [P('$1,000,000 本金年度税前收益', 'table_cell_left'),
         P('$35,000', 'table_cell'),
         P('$50,000', 'table_cell'),
         P('$80,000', 'table_cell'),
         P('$100,000', 'table_cell')],
        [P('收入类型', 'table_cell_left'),
         P('利息收入\n（100%应税）', 'red'),
         P('资本利得\n（50%应税）', 'green'),
         P('资本利得\n（50%应税）', 'green'),
         P('资本利得\n（50%应税）', 'green')],
        [P('应税收入（Taxable Income）', 'table_cell_left'),
         P('$35,000', 'red'),
         P('$25,000', 'green'),
         P('$40,000', 'green'),
         P('$50,000', 'green')],
        [P('估算税额\n（边际税率43.41%）', 'table_cell_left'),
         P('$15,194', 'red'),
         P('$10,853', 'green'),
         P('$17,364', 'green'),
         P('$21,705', 'green')],
        [P('税后净收益', 'table_cell_bold'),
         P('$19,806', 'red'),
         P('$39,147', 'green'),
         P('$62,636', 'green'),
         P('$78,295', 'green')],
        [P('较GIC税后净收益多赚', 'table_cell_bold'),
         P('—', 'table_cell'),
         P('+$19,341', 'green'),
         P('+$42,830', 'green'),
         P('+$58,489', 'green')],
    ]
    tax_t = Table(tax_data, colWidths=[50*mm, 32*mm, 32*mm, 32*mm, 32*mm])
    tax_t.setStyle(base_table_style())
    tax_t.setStyle(TableStyle([
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#D5F5E3')),
        ('BACKGROUND', (0,6), (-1,6), GOLD_LIGHT),
        ('FONTNAME', (0,5), (-1,6), CN_BOLD),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#C0392B')),
        ('BACKGROUND', (2,0), (-1,0), colors.HexColor('#27AE60')),
    ]))
    story.append(tax_t)
    story.append(sp(6))
    story.append(P(
        '※ 税率以安省2024年最高边际税率43.41%为参考，实际税务情况因个人收入结构而有所差异，'
        '请咨询专业税务顾问获取个性化建议。资本利得税率适用于非注册账户（Non-registered）下的投资收益。',
        'note'))

    story.append(PageBreak())

    # ── 5.3 全面对比矩阵 ──────────────────────────────────
    story.append(P('▌ 5.3 产品综合对比矩阵', 'sub_title'))

    matrix_data = [
        [P('对比维度', 'table_header'),
         P('银行 GIC', 'table_header'),
         P('分离账户基金', 'table_header'),
         P('优势方', 'table_header')],
        [P('预期回报率', 'table_cell_left'),
         P('3.0%–3.7%（固定）', 'red'),
         P('5%–12%（历史参考）', 'green'),
         P('分离基金 ✓', 'green')],
        [P('回报类型', 'table_cell_left'),
         P('利息收入（全额应税）', 'red'),
         P('资本利得（50%应税）', 'green'),
         P('分离基金 ✓', 'green')],
        [P('流动性', 'table_cell_left'),
         P('到期才可赎回，提前罚息', 'red'),
         P('随时可赎回，灵活性强', 'green'),
         P('分离基金 ✓', 'green')],
        [P('本金保障', 'table_cell_left'),
         P('CDIC保险上限$100,000', 'table_cell'),
         P('合同保证75%–100%（到期或身故）', 'green'),
         P('分离基金 ✓', 'green')],
        [P('身故受益人', 'table_cell_left'),
         P('进入遗产，需认证', 'red'),
         P('直接给付受益人，免认证', 'green'),
         P('分离基金 ✓', 'green')],
        [P('债权人保护', 'table_cell_left'),
         P('无', 'red'),
         P('指定直系亲属受益人时受保护', 'green'),
         P('分离基金 ✓', 'green')],
        [P('遗产认证费', 'table_cell_left'),
         P('需缴纳（安省约1.5%）', 'red'),
         P('无需（直接传承）', 'green'),
         P('分离基金 ✓', 'green')],
        [P('投资多样性', 'table_cell_left'),
         P('单一固定收益', 'table_cell'),
         P('多元化基金组合，专业管理', 'green'),
         P('分离基金 ✓', 'green')],
        [P('通胀抗性', 'table_cell_left'),
         P('低（固定利率）', 'red'),
         P('较强（股票资产抗通胀）', 'green'),
         P('分离基金 ✓', 'green')],
        [P('开户复杂度', 'table_cell_left'),
         P('简单', 'green'),
         P('需要KYC及风险评估', 'table_cell'),
         P('GIC ✓', 'green')],
    ]
    matrix_t = Table(matrix_data, colWidths=[50*mm, 55*mm, 55*mm, 30*mm])
    matrix_t.setStyle(base_table_style())
    matrix_t.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_GRAY),
    ]))
    story.append(matrix_t)
    story.append(sp(10))

    # ═══════════════════════════════════════════════════════
    # 6. 10年/20年遗产规划对比
    # ═══════════════════════════════════════════════════════
    story += section_header('六、长期遗产规划价值：20年复利对比',
                            '以 $1,000,000 本金，分析GIC vs 分离基金的长期财富积累差距')

    legacy_data = [
        [P('投资工具', 'table_header'),
         P('年化回报', 'table_header'),
         P('10年后资产', 'table_header'),
         P('20年后资产', 'table_header'),
         P('20年税后净值\n（估算）', 'table_header'),
         P('20年净资产增加', 'table_header')],
        [P('银行GIC（滚动3年期）', 'table_cell_left'),
         P('3.3%', 'table_cell'),
         P(fmt(grow(p, 0.033, 10)), 'table_cell'),
         P(fmt(grow(p, 0.033, 20)), 'table_cell'),
         P(fmt(grow(p, 0.033*0.567, 20)), 'red'),  # after-tax approx
         P(fmt(grow(p, 0.033*0.567, 20) - p), 'red')],
        [P('中低风险分离基金', 'table_cell_left'),
         P('5.0%', 'table_cell'),
         P(fmt(grow(p, 0.05, 10)), 'table_cell'),
         P(fmt(grow(p, 0.05, 20)), 'table_cell'),
         P(fmt(grow(p, 0.05, 20) - (grow(p,0.05,20)-p)*0.5*0.4341), 'green'),
         P(fmt(grow(p,0.05,20) - (grow(p,0.05,20)-p)*0.5*0.4341 - p), 'green')],
        [P('中等风险分离基金', 'table_cell_left'),
         P('8.0%', 'table_cell'),
         P(fmt(grow(p, 0.08, 10)), 'table_cell'),
         P(fmt(grow(p, 0.08, 20)), 'table_cell'),
         P(fmt(grow(p, 0.08, 20) - (grow(p,0.08,20)-p)*0.5*0.4341), 'green'),
         P(fmt(grow(p,0.08,20) - (grow(p,0.08,20)-p)*0.5*0.4341 - p), 'green')],
        [P('中高风险分离基金', 'table_cell_left'),
         P('10.0%', 'table_cell'),
         P(fmt(grow(p, 0.10, 10)), 'table_cell'),
         P(fmt(grow(p, 0.10, 20)), 'table_cell'),
         P(fmt(grow(p, 0.10, 20) - (grow(p,0.10,20)-p)*0.5*0.4341), 'green'),
         P(fmt(grow(p,0.10,20) - (grow(p,0.10,20)-p)*0.5*0.4341 - p), 'green')],
    ]
    legacy_t = Table(legacy_data, colWidths=[44*mm, 20*mm, 28*mm, 28*mm, 32*mm, 28*mm])
    legacy_t.setStyle(base_table_style())
    legacy_t.setStyle(TableStyle([
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FEF9E7')),
        ('BACKGROUND', (0,2), (-1,4), colors.HexColor('#EAFAF1')),
    ]))
    story.append(legacy_t)
    story.append(sp(6))
    story.append(P(
        '※ 20年税后净值估算：资本利得税以50%纳入应税，边际税率43.41%；GIC利息收入100%应税。'
        '仅供参考，不考虑每年复利分配的具体税务时间节点。', 'note'))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════
    # 7. 常见问题
    # ═══════════════════════════════════════════════════════
    story += section_header('七、客户常见问题解答（FAQ）')

    faqs = [
        ('分离账户基金与普通共同基金（Mutual Fund）有何区别？',
         '分离账户基金是以保险合同形式设立的投资工具，具有到期保证、身故保证、债权人保护和绕过遗产认证等保险特有功能，'
         '而普通共同基金不具备这些保障功能。两者的投资底层资产可以相似，但法律架构和保障机制截然不同。'),
        ('如果市场大跌，我的本金安全吗？',
         'Equitable Life的分离账户基金提供75%–100%的到期本金保证（持有至到期日，通常为10年）及身故受益保证。'
         '即便市场下跌，只要持有至到期，您将至少拿回75%的投入本金。这是GIC和共同基金都无法提供的保障。'),
        ('分离账户基金的费用是否比GIC高？',
         'MER（管理费）通常在2%–3%之间，高于GIC（GIC无额外管理费，但银行赚取利差）。'
         '然而，考虑到分离基金更高的历史回报潜力、税务效率及保险保障价值，综合性价比更为优越。'),
        ('资金需要锁定多久？',
         '与GIC不同，分离账户基金通常可以随时赎回，无硬性锁定期（但赎回会影响保证额度的重置计算）。'
         '为了获得最优的到期保证，建议持有至合同规定的到期日。'),
        ('如何指定受益人？是否需要律师见证？',
         '受益人指定直接在保险合同中完成，无需律师见证，简便快捷。受益人身故时可直接从保险公司领取款项，'
         '无需通过遗产认证程序，大幅节省时间和费用（安省遗嘱认证费约为遗产总值的1.5%）。'),
    ]

    for q, a in faqs:
        story.append(KeepTogether([
            P(f'Q：{q}', 'body_bold'),
            P(f'A：{a}', 'body'),
            sp(4),
        ]))
    story.append(thin_line())

    # ═══════════════════════════════════════════════════════
    # 8. 免责声明
    # ═══════════════════════════════════════════════════════
    story += section_header('八、重要声明与免责条款')

    disclaimers = [
        '本报告由 Triton Wealth Management Corporation（富瑞财富管理）制作，仅供参考，不构成任何形式的投资建议或保证。',
        '所有历史回报数据来源于 Equitable Life FundData（fundata.com），数据截至2025年4月30日，已扣除管理费用（MER）。',
        '过去的投资回报不保证未来结果。分离账户基金的价值会随市场波动而变化，投资者可能损失部分或全部本金。',
        '本报告中的税务分析仅供参考，实际税务影响因个人情况而有所差异。请在做出任何投资或税务决策前咨询持牌注册的税务或法律顾问。',
        '本报告所涉及的产品为分离账户基金（Segregated Fund），属保险合同，受相关省份保险法规监管，受益人保证不受CDIC存款保险覆盖。',
        'GIC利率参考2025年加拿大主要银行市场利率，实际利率以各银行当时公布为准。',
        'Triton Wealth Management Corporation 持有相关金融产品销售资质，所有理财顾问均受省级监管机构监督。',
    ]
    for i, d in enumerate(disclaimers, 1):
        story.append(P(f'{i}. {d}', 'note'))
        story.append(sp(2))

    story.append(sp(12))
    story.append(gold_line())

    # Footer contact
    contact_data = [
        [P('Triton Wealth Management Corporation', 'highlight'),
         P('富瑞财富管理', 'highlight')],
        [P('专业、诚信、传承财富', 'body'), P('Professional · Trustworthy · Legacy', 'body')],
        [P('www.tritonwealth.ca', 'body'), P('info@tritonwealth.ca', 'body')],
    ]
    contact_t = Table(contact_data, colWidths=[85*mm, 85*mm])
    contact_t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8F3E8')),
    ]))
    story.append(contact_t)

    return story


# ══════════════════════════════════════════════════════════════
#  PAGE TEMPLATE (header/footer on every page)
# ══════════════════════════════════════════════════════════════
def draw_cover(canv, doc):
    W, H = A4
    logo_path = LOGO

    # Navy background
    canv.setFillColor(NAVY)
    canv.rect(0, 0, W, H, fill=1, stroke=0)

    # Gold top stripe
    canv.setFillColor(GOLD)
    canv.rect(0, H - 12*mm, W, 12*mm, fill=1, stroke=0)

    # Gold bottom stripe
    canv.rect(0, 0, W, 8*mm, fill=1, stroke=0)

    # Decorative side gold bar
    canv.setFillColor(GOLD_DARK)
    canv.rect(0, 0, 6*mm, H, fill=1, stroke=0)

    # Logo
    logo_w = 70*mm
    logo_h = 70*mm
    logo_x = (W - logo_w) / 2
    logo_y = H - 60*mm - logo_h
    if os.path.exists(logo_path):
        canv.setFillColor(WHITE)
        canv.roundRect(logo_x - 8*mm, logo_y - 5*mm,
                       logo_w + 16*mm, logo_h + 10*mm,
                       radius=6*mm, fill=1, stroke=0)
        canv.drawImage(logo_path, logo_x, logo_y,
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, anchor='c',
                       mask='auto')

    # Title
    canv.setFillColor(WHITE)
    canv.setFont(CN_BOLD, 24)
    canv.drawCentredString(W/2, logo_y - 22*mm, '投资组合建议报告')

    canv.setFillColor(GOLD_LIGHT)
    canv.setFont(CN_FONT, 13)
    canv.drawCentredString(W/2, logo_y - 33*mm,
                           'Equitable Life 保险分红基金 · 定制投资方案')

    # Divider
    canv.setStrokeColor(GOLD)
    canv.setLineWidth(1.5)
    canv.line(W*0.2, logo_y - 40*mm, W*0.8, logo_y - 40*mm)

    # Info box
    box_y = logo_y - 95*mm
    canv.setFillColor(colors.HexColor('#243660'))
    canv.roundRect(20*mm, box_y, W - 40*mm, 48*mm,
                   radius=4*mm, fill=1, stroke=0)
    canv.setStrokeColor(GOLD)
    canv.setLineWidth(1)
    canv.roundRect(20*mm, box_y, W - 40*mm, 48*mm,
                   radius=4*mm, fill=0, stroke=1)

    items = [
        ('参考本金', '$1,000,000 CAD'),
        ('风险等级', '中低  |  中等  |  中高'),
        ('产品类型', '分离账户基金（Segregated Fund）'),
        ('报告日期', '2025年5月'),
    ]
    row_h = 10*mm
    for i, (label, value) in enumerate(items):
        y = box_y + 38*mm - i * row_h
        canv.setFont(CN_FONT, 10)
        canv.setFillColor(GOLD)
        canv.drawString(28*mm, y, label + '：')
        canv.setFillColor(WHITE)
        canv.drawString(65*mm, y, value)

    # Footer
    canv.setFillColor(GOLD_LIGHT)
    canv.setFont(CN_FONT, 8)
    canv.drawCentredString(W/2, 12*mm,
        'Triton Wealth Management Corporation  |  富瑞财富管理')


class PageDecorator:
    def __init__(self, logo_path):
        self.logo = logo_path

    def __call__(self, canv, doc):
        W, H = A4
        page = doc.page

        # Top header bar
        canv.setFillColor(NAVY)
        canv.rect(0, H - 18*mm, W, 18*mm, fill=1, stroke=0)

        # Gold accent line under header
        canv.setFillColor(GOLD)
        canv.rect(0, H - 20*mm, W, 2*mm, fill=1, stroke=0)

        # Logo in header (small)
        if os.path.exists(self.logo):
            canv.drawImage(self.logo, 10*mm, H - 16*mm,
                           width=22*mm, height=12*mm,
                           preserveAspectRatio=True, anchor='sw',
                           mask='auto')

        # Header text
        canv.setFillColor(WHITE)
        canv.setFont(CN_BOLD, 9)
        canv.drawCentredString(W/2, H - 13*mm, '富瑞财富管理 | Triton Wealth Management')
        canv.setFont(CN_FONT, 7)
        canv.setFillColor(GOLD_LIGHT)
        canv.drawRightString(W - 10*mm, H - 13*mm, 'Equitable Life 分离账户基金 投资组合报告')

        # Bottom footer
        canv.setFillColor(NAVY)
        canv.rect(0, 0, W, 12*mm, fill=1, stroke=0)
        canv.setFillColor(GOLD)
        canv.rect(0, 12*mm, W, 1.5*mm, fill=1, stroke=0)

        canv.setFillColor(WHITE)
        canv.setFont(CN_FONT, 7)
        canv.drawString(10*mm, 4*mm, '仅供参考，不构成投资建议。过去表现不代表未来回报。')
        canv.drawRightString(W - 10*mm, 4*mm, f'第 {page - 1} 页')

        canv.setFillColor(GOLD_LIGHT)
        canv.drawCentredString(W/2, 4*mm, '© 2025 Triton Wealth Management Corporation')


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
def main():
    decorator = PageDecorator(LOGO)

    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=18*mm,
        rightMargin=18*mm,
        topMargin=25*mm,
        bottomMargin=18*mm,
        title='Triton Wealth - Equitable Life 分离账户基金 投资组合报告',
        author='Triton Wealth Management Corporation',
        subject='Investment Portfolio Report',
    )

    story = build_story()
    doc.build(story, onFirstPage=draw_cover, onLaterPages=decorator)
    print(f"\nDone! PDF generated: {OUTPUT}")


if __name__ == '__main__':
    main()
