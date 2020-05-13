#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys, logging
import cg_algorithms as alg
from typing import Optional
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    qApp,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsItem,
    QListWidget,
    QHBoxLayout,
    QWidget,
    QColorDialog,
    QInputDialog,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFileDialog,
    QStyleOptionGraphicsItem)
from PyQt5.QtGui import QPainter, QMouseEvent, QColor, QImage, QPen
from PyQt5.QtCore import QRectF, Qt

class MyCanvas(QGraphicsView):
    """
    画布窗体类，继承自QGraphicsView，采用QGraphicsView、QGraphicsScene、QGraphicsItem的绘图框架
    """
    def __init__(self, *args):
        super().__init__(*args)
        self.main_window = None
        self.list_widget = None
        self.item_dict = {}
        self.selected_id = ''

        self.status = ''
        self.temp_algorithm = ''
        self.temp_id = ''
        self.temp_item = None
        self.temp_pen_color = QColor(0, 0, 0)
        self.polygon_cnt = 0
        self.mouse_pos = []
        self.aux_item = None #辅助图元，用于裁剪等功能
    
    def delete_item(self, item_id):
        if(item_id == self.selected_id):
            self.selected_id = ''
        self.scene().removeItem(self.item_dict[item_id])
        self.updateScene([self.sceneRect()])
        item_list = self.main_window.list_widget.findItems(item_id + ' ' + self.item_dict[item_id].item_type, Qt.MatchExactly)
        self.main_window.list_widget.removeItemWidget(item_list[0])
        del self.item_dict[item_id]
        

    def start_draw_line(self, algorithm, item_id):
        self.status = 'line'
        self.temp_algorithm = algorithm
        self.temp_id = item_id
        # logging.debug('draw line with color: {}'.format(self.temp_pen_color))
    
    def start_draw_polygon(self, algorithm, item_id):
        self.status = 'polygon'
        self.temp_algorithm = algorithm
        self.temp_id = item_id
        self.item_dict[self.temp_id] = []
        # logging.debug('start draw polygon.')

    def start_draw_ellipse(self, item_id):
        self.status = 'ellipse'
        self.temp_algorithm = ''
        self.temp_id = item_id
    
    def start_translate_item(self):
        if(self.selected_id == ''):
            self.main_window.statusBar().showMessage('请选择待平移图元')
            return
        self.status = 'translate'
        self.temp_item = self.item_dict[self.selected_id]
    
    def start_clip_line(self, algorithm):
        if(self.selected_id == ''):
            self.main_window.statusBar().showMessage('请选择待裁剪图元')
            return
        self.status = 'clip'
        self.temp_item = self.item_dict[self.selected_id]
        self.temp_algorithm = algorithm
    
    def start_scale_item(self):
        if(self.selected_id == ''):
            self.main_window.statusBar().showMessage('请选择待缩放图元')
            return
        self.status = 'scale'
        self.temp_item = self.item_dict[self.selected_id]
        self.temp_item.scale_flag = True
        self.updateScene([self.sceneRect()])

    def finish_draw(self):
        self.temp_id = self.main_window.new_id()

    def clear_selection(self):
        if self.selected_id != '':
            # self.main_window.list_widget.clearSelection()
            self.main_window.list_widget.setCurrentItem(None)
            self.item_dict[self.selected_id].selected = False
            self.selected_id = ''

    def selection_changed_from_list(self, selected):
        if selected == '':
            return
        logging.debug('select ' + selected)
        i = 0
        while selected[i].isdigit():
            i += 1
        selected_id = selected[0:i]
        logging.debug('selected id = ' + selected_id)
        self.selection_changed_by_id(selected_id)

    def selection_changed_by_id(self, selected_id):
        if selected_id == '':
            return
        # logging.debug('select ' + selected_id)
        self.main_window.statusBar().showMessage('图元选择： %s' % selected_id)
        if self.selected_id != '':
            self.item_dict[self.selected_id].selected = False
            self.item_dict[self.selected_id].update()
        self.selected_id = selected_id
        self.item_dict[selected_id].selected = True
        self.item_dict[selected_id].update()
        self.status = ''
        self.updateScene([self.sceneRect()])    

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = self.mapToScene(event.localPos().toPoint())
        x = int(pos.x())
        y = int(pos.y())
        if self.status == 'line':
            # 绘制直线
            self.temp_item = MyItem(self.temp_id, self.status, [[x, y], [x, y]], self.temp_algorithm, self.temp_pen_color)
            self.scene().addItem(self.temp_item)
        elif self.status == 'polygon':
            # 绘制多边形
            if not self.item_dict[self.temp_id]:
                self.temp_item = MyItem(self.temp_id, 'line', [[x, y], [x, y]], self.temp_algorithm, self.temp_pen_color)
            else:
                last_point = self.item_dict[self.temp_id][-1].p_list[1]
                self.temp_item = MyItem(self.temp_id, 'line', [last_point, [x, y]], self.temp_algorithm, self.temp_pen_color)
            self.scene().addItem(self.temp_item)
            self.item_dict[self.temp_id].append(self.temp_item)
        elif self.status == 'ellipse':
            # 绘制椭圆
            self.temp_item = MyItem(self.temp_id, self.status, [[x,y], [x,y]], self.temp_algorithm, self.temp_pen_color)
            self.scene().addItem(self.temp_item)
        elif self.status == 'translate':
            self.mouse_pos = [x,y]
            if not self.temp_item.in_boundingRect(x,y):
                self.status = ''
                self.temp_item.selected = False
                self.main_window.statusBar().showMessage('平移结束')
        elif self.status == 'clip':
            self.aux_item = MyItem('aux', 'aux_rect', [[x,y], [x,y]], '', QColor(255, 0, 0))
            self.scene().addItem(self.aux_item)
        elif self.status == 'scale':
            self.mouse_pos = [x,y]
            self.temp_item.center = self.temp_item.get_scale_center(x, y)
            if not self.temp_item.center:
                self.status = ''
                self.temp_item.scale_flag = False
                self.temp_item.selected = False
                self.main_window.statusBar().showMessage('缩放结束')
        elif self.status == '':
            # 选择图元
            selected_items = self.items(x,y)
            if len(selected_items) > 0:
                selected_id = getattr(selected_items[0], 'id')
                self.selection_changed_by_id(selected_id)
            else:
                self.main_window.statusBar().showMessage('空闲：(%d, %d)' % (x, y))
                self.clear_selection()
        self.updateScene([self.sceneRect()])
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = self.mapToScene(event.localPos().toPoint())
        x = int(pos.x())
        y = int(pos.y())
        if self.status == 'line':
            self.temp_item.p_list[1] = [x, y]
        elif self.status == 'polygon':
            self.temp_item.p_list[1] = [x, y]
        elif self.status == 'ellipse':
            self.temp_item.p_list[1] = [x, y]
        elif self.status == 'translate':
            self.main_window.statusBar().showMessage('平移 %s：(%d, %d)' % (self.selected_id, x,y))
            new_p_list = alg.translate(self.temp_item.p_list, x-self.mouse_pos[0], y-self.mouse_pos[1])
            self.mouse_pos = [x,y]
            self.temp_item.p_list = new_p_list
        elif self.status == 'clip':
            self.aux_item.p_list[1] = [x,y]
            self.main_window.statusBar().showMessage('裁剪 %s：(%d, %d) - (%d, %d)' % (self.selected_id, self.aux_item.p_list[0][0], self.aux_item.p_list[0][1], x,y))
        elif self.status == 'scale':
            self.temp_item.scale(x)
            self.mouse_pos = [x,y]
            self.main_window.statusBar().showMessage('缩放 %s: (%d, %d)' % (self.selected_id, x, y))
        elif self.status == '':
            self.main_window.statusBar().showMessage('空闲：(%d, %d)' % (x,y))
        self.updateScene([self.sceneRect()])
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.status == 'line':
            self.item_dict[self.temp_id] = self.temp_item
            self.list_widget.addItem(self.temp_id + ' ' + self.status)
            self.finish_draw()
            self.status = ''
        elif self.status == 'polygon':
            pass
        elif self.status == 'ellipse':
            self.item_dict[self.temp_id] = self.temp_item
            self.list_widget.addItem(self.temp_id + ' ' +  self.status)
            self.finish_draw()
            self.status = ''
        elif self.status == 'translate':
            self.main_window.statusBar().showMessage('平移完成')
            # self.status = ''
        elif self.status == 'clip':
            new_p_list = alg.clip(self.temp_item.p_list, self.aux_item.p_list[0][0], self.aux_item.p_list[0][1], self.aux_item.p_list[1][0], self.aux_item.p_list[1][1], self.temp_algorithm)
            if not new_p_list:
                self.delete_item(self.selected_id)
            else:
                self.temp_item.p_list = new_p_list
            self.main_window.statusBar().showMessage('裁剪完成')
            self.status = ''
            self.scene().removeItem(self.aux_item)
        elif self.status == 'scale':
            self.main_window.statusBar().showMessage('缩放完成')
            # self.status = ''
        self.updateScene([self.sceneRect()])
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.status == 'polygon':
            # 多边形双击闭合
            if not self.item_dict[self.temp_id]:
                return
            p_list = [self.item_dict[self.temp_id][0].p_list[0],]
            for line_item in self.item_dict[self.temp_id]:
                p_list.append(line_item.p_list[1])
                self.scene().removeItem(line_item)
            self.temp_item = MyItem(self.temp_id, 'polygon', p_list, self.temp_algorithm, self.temp_pen_color)
            self.scene().addItem(self.temp_item)
            self.item_dict[self.temp_id] = self.temp_item
            self.list_widget.addItem(self.temp_id +' ' + self.status)
            self.finish_draw()
            self.status = ''
        self.updateScene([self.sceneRect()])
        super().mouseDoubleClickEvent(event)

    def get_pos(self, event: QMouseEvent) -> [int, int]:
        pos = self.mapToScene(event.localPos().toPoint())
        return [int(pos.x()), int(pos.y())]


class MyItem(QGraphicsItem):
    """
    自定义图元类，继承自QGraphicsItem
    """
    def __init__(self, item_id: str, item_type: str, p_list: list, algorithm: str = '', color = QColor(0,0,0), parent: QGraphicsItem = None):
        """
        :param item_id: 图元ID
        :param item_type: 图元类型，'line'、'polygon'、'ellipse'、'curve'等
        :param p_list: 图元参数
        :param algorithm: 绘制算法，'DDA'、'Bresenham'、'Bezier'、'B-spline'等
        :param parent:
        """
        super().__init__(parent)
        self.id = item_id           # 图元ID
        self.item_type = item_type  # 图元类型，'line'、'polygon'、'ellipse'、'curve'等
        self.p_list = p_list        # 图元参数
        self.algorithm = algorithm  # 绘制算法，'DDA'、'Bresenham'、'Bezier'、'B-spline'等
        self.selected = False
        self.color = color
        self.scale_flag = False
        self.center = [] # 操作中心，用于缩放和旋转
        # logging.debug('create MyItem {} with p_list={}'.format(item_type, p_list))

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        draw_dict = {
            'line': alg.draw_line,
            'polygon': alg.draw_polygon,
            'ellipse': alg.draw_ellipse,
            'curve': alg.draw_curve,
            'aux_rect': alg.draw_rect
        }
        item_pixels = draw_dict[self.item_type](self.p_list, self.algorithm)
        for p in item_pixels:
            if self.item_type != 'aux_rect':
                painter.setPen(self.color) 
            else:
                pen = QPen()
                pen.setStyle(Qt.DashLine)
                pen.setBrush(Qt.red)
                painter.setPen(pen)
            painter.drawPoint(*p)
        if self.selected:
            pen = QPen()
            pen.setStyle(Qt.DashLine)
            pen.setBrush(Qt.red)
            painter.setPen(pen)
            painter.drawRect(self.boundingRect())
            if self.scale_flag:
                self.scale_vertex(painter)

    def get_bound(self):
        """得到图元的左上角和右下角点的坐标
        :return: [[minx, miny], [maxx, maxy]]
        """
        min_x, min_y, max_x, max_y = 1001, 1001, -1, -1
        if self.item_type == 'line':
            x0, y0 = self.p_list[0]
            x1, y1 = self.p_list[1]
            min_x = min(x0, x1)
            min_y = min(y0, y1)
            max_x = max(x0, x1)
            max_y = max(y0, y1)
        elif self.item_type == 'polygon':
            for [xx, yy] in self.p_list:
                min_x, min_y, max_x, max_y = min(xx, min_x), min(yy, min_y), max(xx, max_x), max(yy, max_y)
        elif self.item_type == 'ellipse':
            x0, y0 = self.p_list[0]
            x1, y1 = self.p_list[1]
            min_x = min(x0, x1)
            min_y = min(y0, y1)
            max_x = max(x0, x1)
            max_y = max(y0, y1)
        elif self.item_type == 'aux_rect':
            min_x, min_y = self.p_list[0]
            max_x, max_y = self.p_list[1]
        elif self.item_type == 'curve':
            pass
        return [[min_x, min_y], [max_x, max_y]]

    def scale_vertex(self, painter):
        """给图元的外接矩形的顶点加上小矩形
        """
        bound_p_list = self.get_bound()
        min_x, min_y = bound_p_list[0]
        max_x, max_y = bound_p_list[1]
        sz = 12
        painter.drawRect(QRectF(min_x-sz/2, min_y-sz/2, sz, sz))
        painter.drawRect(QRectF(min_x-sz/2, max_y-sz/2, sz, sz))
        painter.drawRect(QRectF(max_x-sz/2, min_y-sz/2, sz, sz))
        painter.drawRect(QRectF(max_x-sz/2, max_y-sz/2, sz, sz))
    
    def get_scale_center(self, x, y):
        """根据鼠标点击的位置返回缩放中心
        """
        bound_p_list = self.get_bound()
        min_x, min_y = bound_p_list[0]
        max_x, max_y = bound_p_list[1]
        half_sz = 6
        if abs(x-min_x) <= half_sz and abs(y-min_y) <= half_sz:
            return [max_x, max_y]
        if abs(x-min_x) <= half_sz and abs(y-max_y) <= half_sz:
            return [max_x, min_y]
        if abs(x-max_x) <= half_sz and abs(y-min_y) <= half_sz:
            return [min_x, max_y]
        if abs(x-max_x) <= half_sz and abs(y-max_y) <= half_sz:
            return [min_x, min_y]
        return []
    
    def scale(self, new_x):
        """根据横坐标增量进行缩放
        """
        s = abs(new_x - self.center[0]) / (self.p_list[1][0] - self.p_list[0][0])
        new_p_list = alg.scale(self.p_list, self.center[0], self.center[1], s)
        self.p_list = new_p_list
    
    def boundingRect(self) -> QRectF:
        bound_p_list = self.get_bound()
        min_x, min_y = bound_p_list[0]
        max_x, max_y = bound_p_list[1]
        return QRectF(min_x-1,  min_y-1, max_x-min_x+2, max_y-min_y+2)
    
    def in_boundingRect(self, x, y):
        bound_p_list = self.get_bound()
        min_x, min_y = bound_p_list[0]
        max_x, max_y = bound_p_list[1]
        return (x <= max_x and x >= min_x and y <= max_y and y >= min_y)


class MainWindow(QMainWindow):
    """
    主窗口类
    """
    def __init__(self):
        super().__init__()
        self.item_cnt = 0
        self.pen_color = QColor(0,0,0)

        self.height = self.width = 600
        self.set_canvas_action()

        # 设置菜单栏
        menubar = self.menuBar()
        file_menu = menubar.addMenu('文件')
        set_pen_act = file_menu.addAction('设置画笔')
        reset_canvas_act = file_menu.addAction('重置画布')
        clear_canvas_act = file_menu.addAction('清空画布')
        save_canvas_act = file_menu.addAction('保存画布')
        save_canvas_act.setShortcut('Ctrl+S')
        exit_act = file_menu.addAction('退出')
        draw_menu = menubar.addMenu('绘制')
        line_menu = draw_menu.addMenu('线段')
        line_naive_act = line_menu.addAction('Naive')
        line_dda_act = line_menu.addAction('DDA')
        line_bresenham_act = line_menu.addAction('Bresenham')
        polygon_menu = draw_menu.addMenu('多边形')
        polygon_dda_act = polygon_menu.addAction('DDA')
        polygon_bresenham_act = polygon_menu.addAction('Bresenham')
        ellipse_act = draw_menu.addAction('椭圆')
        curve_menu = draw_menu.addMenu('曲线')
        curve_bezier_act = curve_menu.addAction('Bezier')
        curve_b_spline_act = curve_menu.addAction('B-spline')
        edit_menu = menubar.addMenu('编辑')
        translate_act = edit_menu.addAction('平移')
        rotate_act = edit_menu.addAction('旋转')
        scale_act = edit_menu.addAction('缩放')
        clip_menu = edit_menu.addMenu('裁剪')
        clip_cohen_sutherland_act = clip_menu.addAction('Cohen-Sutherland')
        clip_liang_barsky_act = clip_menu.addAction('Liang-Barsky')

        # 连接信号和槽函数
        #-------------------文件--------------------
        exit_act.triggered.connect(qApp.quit)
        clear_canvas_act.triggered.connect(self.clear_canvas_action)
        reset_canvas_act.triggered.connect(self.reset_canvas_action)
        set_pen_act.triggered.connect(self.set_pen_action)
        # -------------------绘制--------------------
        save_canvas_act.triggered.connect(self.save_canvas_action)
        line_naive_act.triggered.connect(self.line_naive_action)
        line_dda_act.triggered.connect(self.line_dda_action)
        line_bresenham_act.triggered.connect(self.line_bresenham_action)
        polygon_dda_act.triggered.connect(self.polygon_dda_action)
        polygon_bresenham_act.triggered.connect(self.polygon_bresenham_action)
        ellipse_act.triggered.connect(self.ellipse_action)
        self.list_widget.currentTextChanged.connect(self.canvas_widget.selection_changed_from_list)
        # -------------------编辑--------------------
        translate_act.triggered.connect(self.translate_action)
        clip_cohen_sutherland_act.triggered.connect(self.clip_cohen_sutherland_action)
        clip_liang_barsky_act.triggered.connect(self.clip_liang_barsky_action)
        scale_act.triggered.connect(self.scale_action)

    def get_id(self):
        return str(self.item_cnt)

    def new_id(self):
        _id = str(self.item_cnt)
        self.item_cnt += 1
        return _id
    
    def set_pen_action(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas_widget.temp_pen_color = color
            # logging.debug('set pen color to {}'.format(color))git

    def line_naive_action(self):
        self.canvas_widget.start_draw_line('Naive', self.get_id())
        self.statusBar().showMessage('Naive算法绘制线段')
        self.canvas_widget.clear_selection()

    def line_dda_action(self):
        self.canvas_widget.start_draw_line('DDA', self.get_id())
        self.statusBar().showMessage('DDA算法绘制线段')
        self.canvas_widget.clear_selection()
    
    def line_bresenham_action(self):
        self.canvas_widget.start_draw_line('Bresenham', self.get_id())
        self.statusBar().showMessage('Bresenham算法绘制线段')
        self.canvas_widget.clear_selection()

    def polygon_dda_action(self):
        self.canvas_widget.start_draw_polygon('DDA', self.get_id())
        self.statusBar().showMessage('DDA算法绘制多边形')
        self.canvas_widget.clear_selection()
    
    def polygon_bresenham_action(self):
        self.canvas_widget.start_draw_polygon('Bresenham', self.get_id())
        self.statusBar().showMessage('Bresenham算法绘制多边形')
        self.canvas_widget.clear_selection()
    
    def ellipse_action(self):
        self.canvas_widget.start_draw_ellipse(self.get_id())
        self.statusBar().showMessage('绘制椭圆')
        self.canvas_widget.clear_selection()
    
    def translate_action(self):
        self.statusBar().showMessage('平移')
        self.canvas_widget.start_translate_item()
    
    def clip_cohen_sutherland_action(self):
        self.statusBar().showMessage('Cohen-Sutherland算法裁剪')
        self.canvas_widget.start_clip_line('Cohen-Sutherland')
    
    def clip_liang_barsky_action(self):
        self.statusBar().showMessage('Liang-Barsky算法裁剪')
        self.canvas_widget.start_clip_line('Liang-Barsky')
    
    def scale_action(self):
        self.statusBar().showMessage('缩放')
        self.canvas_widget.start_scale_item()
        

    def clear_canvas_action(self):
        """清空画布
        """
        self.canvas_widget.resetCachedContent()
        for item_id in range(0, self.item_cnt-1):
            del self.canvas_widget.item_dict[str(item_id)]
            logging.debug('delete item %d' % item_id)
        self.item_cnt = 0
    
    def reset_canvas_action(self):
        self.clear_canvas_action()
        while True:
            width, ok = QInputDialog.getInt(self, '重置画布', '请输入画布宽度：（单位：像素）')
            if ok and width <= 1000 and width >= 100:
                self.width = width
                logging.debug('set width to {}'.format(self.width))
                break
            elif not ok: 
                break
        while True:
            height, ok = QInputDialog.getInt(self, '重置画布', '请输入画布高度：（单位：像素）')
            if ok and height <= 1000 and height >= 100:
                self.height = height
                logging.debug('set height to {}'.format(self.height))
                break
            elif not ok: 
                break
        del self.scene
        del self.canvas_widget
        del self.hbox_layout
        del self.list_widget
        self.item_cnt = 0
        self.set_canvas_action()
    
    def save_canvas_action(self):
        path = QFileDialog.getSaveFileName(parent=self, caption='保存画布',filter='Images(*.bmp)')
        logging.debug('Save canvas to {}'.format(path))
        image = self.canvas_widget.grab(self.canvas_widget.sceneRect().toRect())
        image.save(path[0])
    
    def set_canvas_action(self):
        # 使用QGraphicsView作为画布
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, self.width, self.height)
        self.canvas_widget = MyCanvas(self.scene, self)
        self.canvas_widget.setFixedSize(self.width+10, self.height+10)
        self.canvas_widget.main_window = self
        # 使用QListWidget来记录已有的图元，并用于选择图元。注：这是图元选择的简单实现方法，更好的实现是在画布中直接用鼠标选择图元
        self.list_widget = QListWidget(self)
        self.list_widget.setMinimumWidth(200)
        self.list_widget.setMaximumWidth(200)
        self.canvas_widget.list_widget = self.list_widget
        # 设置主窗口的布局
        self.hbox_layout = QHBoxLayout()
        self.hbox_layout.addWidget(self.canvas_widget)
        self.hbox_layout.addWidget(self.list_widget, stretch=1)
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.hbox_layout)
        self.setCentralWidget(self.central_widget)
        self.statusBar().showMessage('新画布：({}*{})'.format(self.height, self.width))
        self.resize(self.width, self.height)
        self.setWindowTitle('CG Demo')
        


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())
