import sys
import logging
import json
import subprocess
import os
import math
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (
    ComboBox,
    PushButton,
    SpinBox,
    PrimaryPushButton,
    TextEdit,
    EditableComboBox,
    MessageBox,
    FluentIcon as FIF,
    Slider,
)

from .common import CURRENT_DIR, MODELS_DIR
from .gpu import GPUManager, GPUDisplayHelper
from .sakura import SAKURA_LIST, SakuraCalculator
from .setting import SETTING
from .ui import *


class RunServerSection(QFrame):
    def __init__(self, title, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setObjectName(title)

        self._init_ui()
        self.refresh_models()
        self.refresh_gpus()
        self.load_presets(SETTING.presets)

        SETTING.model_sort_option_changed.connect(self.refresh_models)

    def _init_ui(self):
        menu_base = self._create_menu_base()
        menu_advance = self._create_advance_menu()

        layout = QVBoxLayout()
        layout.addLayout(menu_base)
        layout.addWidget(menu_advance)
        layout.insertStretch(-1)
        self.setLayout(layout)

        self.context_length_input.valueChanged.connect(self.update_slider_from_input)
        self.context_length.valueChanged.connect(self.update_context_per_thread)
        self.n_parallel_spinbox.valueChanged.connect(self.update_context_per_thread)
        self.update_context_per_thread()

    def _create_menu_base(self):
        self.benchmark_button = PushButton(FIF.UNIT, "性能测试")
        self.run_and_share_button = PushButton(FIF.IOT, "启动/共享")
        self.run_button = PrimaryPushButton(FIF.PLAY, "启动")

        buttons_group = UiButtonGroup(
            UiButton("高级设置", FIF.MORE, self.toggle_advanced_settings),
            self.benchmark_button,
            self.run_and_share_button,
            self.run_button,
        )

        self.context_per_thread_label = QLabel()

        return UiCol(
            buttons_group,
            UiOptionRow("模型", self._create_model_selection_layout()),
            UiOptionRow("显卡", self._create_gpu_selection_layout()),
            UiOptionRow(
                "上下文长度 -c",
                self._create_context_length_layout(),
                label_width=74,
            ),
            UiOptionRow(
                "并发数量 -np",
                UiSlider(self, "n_parallel", 1, 1, 32, 1, spinbox_fixed_width=140),
                label_width=74,
            ),
            self.context_per_thread_label,
        )

    def _create_preset_options(self):
        self.config_preset_combo = EditableComboBox()
        self.config_preset_combo.currentIndexChanged.connect(self.load_selected_preset)
        SETTING.presets_changed.connect(self.load_presets)

        return UiRow(
            (self.config_preset_combo, 1),
            (UiButton("保存", FIF.SAVE, self.save_preset), 0),
        )

    def _create_ip_port_log_option(self):
        self.host_input = UiLineEdit("", "127.0.0.1")
        self.port_input = UiLineEdit("", "8080")
        self.gpu_layers_spinbox = SpinBox()
        self.gpu_layers_spinbox.setRange(0, 200)
        self.gpu_layers_spinbox.setValue(200)
        return UiRow(
            UiOptionCol("主机地址 --host", self.host_input),
            UiOptionCol("端口 --port", self.port_input),
            UiOptionCol("GPU层数 -ngl", self.gpu_layers_spinbox),
        )

    def _create_benchmark_layout(self):
        self.npp_input = UiLineEdit("Prompt数量", "512")
        self.ntg_input = UiLineEdit("生成文本数量", "128")
        self.npl_input = UiLineEdit("并行Prompt数量", "1,2,4,8")
        return UiRow(
            UiOptionCol("Prompt数量 -npp", self.npp_input),
            UiOptionCol("生成文本数量 -ntg", self.ntg_input),
            UiOptionCol("并行Prompt数量 -npl", self.npl_input),
        )

    def _create_advance_menu(self):
        self.flash_attention_check = UiCheckBox("启用 Flash Attention -fa", True)
        self.no_mmap_check = UiCheckBox("启用 --no-mmap", True)
        layout_extra_options = UiRow(
            self.flash_attention_check,
            self.no_mmap_check,
            None,
        )
        layout_extra_options.setContentsMargins(0, 0, 0, 0)  # 设置内部边距

        self.llamacpp_override = UiLineEdit("覆盖默认llamacpp路径（可选）", "")

        self.command_template = TextEdit()
        self.command_template.setAcceptRichText(False)
        self.command_template.setPlaceholderText(
            "\n".join(
                [
                    "自定义命令模板，其中",
                    "- %cmd%会替换成UI生成的完整命令",
                    "- %cmd_raw%会被替换成UI生成的命令和模型选项，但不包括其他选项",
                ]
            )
        )

        layout = UiCol(
            UiHLine(),
            layout_extra_options,
            UiOptionRow("配置预设选择", self._create_preset_options()),
            self._create_ip_port_log_option(),
            self._create_benchmark_layout(),
            self.llamacpp_override,
            self.command_template,
        )
        layout.setContentsMargins(0, 0, 0, 0)  # 确保布局的边距也被移除
        self.menu_advance = QFrame(self)
        self.menu_advance.setLayout(layout)
        if SETTING.remember_advanced_state:
            self.menu_advance.setVisible(SETTING.advanced_state)
        else:
            self.menu_advance.setVisible(False)
        return self.menu_advance

    def _create_context_length_layout(self):
        layout = QHBoxLayout()
        self.context_length = Slider(Qt.Horizontal, self)
        self.context_length.setRange(0, 10000)
        self.context_length.setPageStep(5)
        self.context_length.setValue(5000)

        self.context_length_input = SpinBox(self)
        self.context_length_input.setRange(256, 131072)
        self.context_length_input.setSingleStep(256)
        self.context_length_input.setValue(2048)
        self.context_length_input.setFixedWidth(140)

        layout.addWidget(self.context_length)
        layout.addWidget(self.context_length_input)

        self.context_length.valueChanged.connect(self.update_context_from_slider)
        self.context_length_input.valueChanged.connect(self.update_slider_from_input)

        return layout

    def _create_model_selection_layout(self):
        layout = QHBoxLayout()
        # 用只读 ComboBox：EditableComboBox 本质是 LineEdit + 下拉按钮，
        # 会同时冒出「清空」按钮，长模型名还会钻到箭头底下，没必要
        self.model_path = ComboBox(self)
        # 不要再设最小宽度：窗口窄时会和「刷新」按钮挤成重叠（两个控件压在一起）
        self.model_path.setMinimumWidth(160)
        self.model_path.currentIndexChanged.connect(self._update_model_tooltip)
        self.refresh_model_button = PushButton(FIF.SYNC, "刷新")
        self.refresh_model_button.clicked.connect(self.refresh_models)
        self.refresh_model_button.setFixedWidth(120)
        layout.addWidget(self.model_path, 1)
        layout.addWidget(self.refresh_model_button, 0)
        return layout

    def _model_display_name(self, path):
        """给模型一个可读名字：优先匹配内置模型列表，其次读 Ollama 仓库的 metadata。"""
        base = os.path.basename(path)
        digest = base[len("sha256-"):] if base.startswith("sha256-") else None
        if digest:
            for sakura in SAKURA_LIST:
                if getattr(sakura, "sha256", "") == digest:
                    return sakura.filename
            meta = os.path.join(
                os.path.dirname(os.path.dirname(path)),
                "metadata",
                f"sha256-{digest}.json",
            )
            try:
                with open(meta, "r", encoding="utf-8") as f:
                    name = json.load(f).get("kv", {}).get("general.name")
                if name:
                    return name
            except (OSError, ValueError):
                pass
        return base

    @staticmethod
    def _is_model_file(path):
        """识别 gguf：正常扩展名，或 Ollama 仓库里没有扩展名的 sha256 blob。"""
        name = os.path.basename(path)
        if name.endswith(".gguf"):
            return True
        if name.startswith("sha256-"):
            try:
                with open(path, "rb") as f:
                    return f.read(4) == b"GGUF"
            except OSError:
                return False
        return False

    def _update_model_tooltip(self, index):
        """悬停时显示完整模型名（下拉框里显示的是省略版）。"""
        path = self.model_path.itemData(index)
        self.model_path.setToolTip(self._model_display_name(path) if path else "")

    @staticmethod
    def _elide_model_name(name, max_chars=30):
        """模型名过长时中间省略：优先按 `-` 分段保留首尾，保住量化等级和扩展名。"""
        if len(name) <= max_chars:
            return name
        parts = name.split("-")
        if len(parts) >= 4:
            shortened = f"{parts[0]}-{parts[1]}-…-{parts[-2]}-{parts[-1]}"
            if len(shortened) <= max_chars + 2:
                return shortened
        head = max_chars // 2 - 1
        tail = max_chars - head - 1
        return f"{name[:head]}…{name[-tail:]}"

    def get_selected_model_path(self):
        """模型下拉框选中的真实路径（可能是 Ollama blob，不含 .gguf 扩展名）。"""
        return self.model_path.currentData() or ""

    def set_selected_model_path(self, path):
        if not path:
            self.model_path.setCurrentIndex(-1)
            return
        for index in range(self.model_path.count()):
            if self.model_path.itemData(index) == path:
                self.model_path.setCurrentIndex(index)
                return
        self.model_path.setCurrentText(path)

    def refresh_models(self):
        self.model_path.clear()
        models = []
        paths = SETTING.model_search_paths.split("\n")
        search_paths = [CURRENT_DIR, MODELS_DIR] + [
            path.strip() for path in paths if path.strip()
        ]
        logging.debug(f"搜索路径: {search_paths}")
        for path in search_paths:
            logging.debug(f"正在搜索路径: {path}")
            if os.path.exists(path):
                logging.debug(f"路径存在: {path}")
                if os.path.isdir(path):
                    logging.debug(f"路径是目录: {path}")
                    for root, dirs, files in os.walk(path):
                        logging.debug(f"正在搜索子目录: {root}")
                        logging.debug(f"文件列表: {files}")
                        for f in files:
                            full_path = os.path.join(root, f)
                            if self._is_model_file(full_path):
                                logging.debug(f"找到模型文件: {full_path}")
                                models.append(full_path)
                else:
                    logging.debug(f"路径不是目录: {path}")
            else:
                logging.debug(f"路径不存在: {path}")

        logging.debug(f"找到的模型文件: {models}")

        # 从设置中获取排序选项
        sort_option = SETTING.model_sort_option

        # 根据选择的排序方式对模型列表进行排序
        if sort_option == "修改时间":
            models.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        elif sort_option == "文件名":
            models.sort(key=lambda x: os.path.basename(x).lower())
        elif sort_option == "文件大小":
            models.sort(key=lambda x: os.path.getsize(x), reverse=True)

        for model in models:
            abs_path = os.path.abspath(model)
            full_name = self._model_display_name(abs_path)
            index = self.model_path.count()
            self.model_path.addItem(self._elide_model_name(full_name))
            self.model_path.setItemData(index, abs_path)

    def _create_gpu_selection_layout(self):
        self.gpu_combo = ComboBox(self)
        button = UiButton("自动配置", FIF.SETTING, self.auto_configure)
        button.setFixedWidth(140)
        return UiRow(self.gpu_combo, button)

    def refresh_gpus(self, keep_selected=False):
        # 保存当前选择的GPU
        current_gpu = self.gpu_combo.currentText() if keep_selected else None

        self.gpu_combo.clear()
        self.nvidia_gpus = self.main_window.gpu_manager.nvidia_gpus
        self.amd_gpus = self.main_window.gpu_manager.amd_gpus

        # 优先添加NVIDIA GPU
        if self.nvidia_gpus:
            self.gpu_combo.addItems(self.nvidia_gpus)

        # 如果有AMD GPU，添加到列表末尾
        if self.amd_gpus:
            self.gpu_combo.addItems(self.amd_gpus)

        if not self.nvidia_gpus and not self.amd_gpus:
            logging.warning("未检测到NVIDIA或AMD GPU")

        self.gpu_combo.addItems(["自动"])

        # 如果需要保持选择，尝试恢复之前的选择
        if keep_selected and current_gpu:
            index = self.gpu_combo.findText(current_gpu)
            if index >= 0:
                self.gpu_combo.setCurrentIndex(index)
            else:
                self.gpu_combo.setCurrentText("自动")

    def context_to_slider(self, context):
        min_value = math.log(256)
        max_value = math.log(131072)
        return int(10000 * (math.log(context) - min_value) / (max_value - min_value))

    def slider_to_context(self, value):
        min_value = math.log(256)
        max_value = math.log(131072)
        return int(math.exp(min_value + (value / 10000) * (max_value - min_value)))

    def update_context_from_slider(self, value):
        context_length = self.slider_to_context(value)
        context_length = max(256, min(131072, context_length))
        context_length = round(context_length / 256) * 256
        self.context_length_input.blockSignals(True)
        self.context_length_input.setValue(context_length)
        self.context_length_input.blockSignals(False)
        self.update_context_per_thread()

    def update_slider_from_input(self, value):

        value = round(value / 256) * 256
        slider_value = self.context_to_slider(value)
        slider_value = max(0, min(10000, slider_value))
        self.context_length.setValue(slider_value)
        self.context_length.update()
        self.update_context_per_thread()

    def update_context_per_thread(self):
        total_context = self.context_length_input.value()
        n_parallel = self.n_parallel_spinbox.value()
        context_per_thread = total_context // n_parallel
        self.context_per_thread_label.setText(
            f"每个工作线程的上下文大小: {context_per_thread}"
        )

    @staticmethod
    def _find_sakura_model(path):
        """按 sha256（Ollama blob）或文件名在内置模型列表里找到对应配置。"""
        name = os.path.basename(path)
        if name.startswith("sha256-"):
            digest = name[len("sha256-"):]
            for model in SAKURA_LIST:
                if getattr(model, "sha256", "") == digest:
                    return model
            return None
        return SAKURA_LIST[name]

    @staticmethod
    def _total_memory_gib():
        """读取系统物理内存（macOS 用 sysctl，其它平台退回 os.sysconf）。"""
        try:
            if sys.platform == "darwin":
                out = subprocess.check_output(
                    ["sysctl", "-n", "hw.memsize"], text=True, timeout=3
                )
                return int(out.strip()) / (1024**3)
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024**3)
        except Exception:
            return None

    def _auto_configure_apple_silicon(self, sakura_model):
        """Apple Silicon 用统一内存估算：留 25% 给系统，其余给模型。"""
        total_gib = self._total_memory_gib()
        if not total_gib:
            UiInfoBarWarning(self, "无法读取系统内存，请手动设置参数")
            return

        available_gib = total_gib * 0.75
        calculator = SakuraCalculator(sakura_model)
        config = calculator.recommend_config(available_gib)

        self.n_parallel_spinbox.setValue(config["n_parallel"])
        self.context_length_input.setValue(config["context_length"])
        usage = calculator.calculate_memory_requirements(config["context_length"])

        UiInfoBarSuccess(
            self,
            f"已按统一内存 {total_gib:.0f} GiB 自动配置: "
            f"context={config['context_length']}, np={config['n_parallel']}, "
            f"预计占用 {usage['total_size_gib']:.2f} GiB",
        )

    def auto_configure(self):
        current_model = self.get_selected_model_path()
        if not current_model:
            UiInfoBarWarning(self, "请先选择一个模型")
            return

        model_name = current_model.split(os.sep)[-1]
        sakura_model = self._find_sakura_model(current_model)
        if not sakura_model:
            UiInfoBarWarning(
                self, "无法找到选中模型的配置信息（该模型不在内置列表中，请手动设置参数）"
            )
            return

        if sys.platform == "darwin":
            self._auto_configure_apple_silicon(sakura_model)
            return

        # 刷新并获取GPU信息
        gpu_manager: GPUManager = self.main_window.gpu_manager
        gpu_manager.detect_gpus()
        selected_gpu_display = self.gpu_combo.currentText()

        # 从显示名称中找到对应的GPU key
        gpu_key = GPUDisplayHelper.find_gpu_key(selected_gpu_display, gpu_manager.gpu_info_map)
        if not gpu_key:
            UiInfoBarWarning(self, "请先选择一个GPU")
            return

        # 检查GPU能力
        gpu_info = gpu_manager.gpu_info_map[gpu_key]
        ability = gpu_manager.check_gpu_ability(selected_gpu_display, model_name)
        if not ability.is_capable:
            UiInfoBarWarning(self, ability.reason)
            return

        available_memory_gib = gpu_info.avail_dedicated_gpu_memory / (2**30)
        total_memory_gib = gpu_info.dedicated_gpu_memory / (2**30)

        try:
            # 创建计算器实例
            calculator = SakuraCalculator(sakura_model)

            # 如果不能获取显存占用，则使用最大显存-2GiB
            if available_memory_gib is None:
                available_memory_gib = total_memory_gib - 2

            # 获取推荐配置
            config = calculator.recommend_config(available_memory_gib)

            # 应用配置
            self.n_parallel_spinbox.setValue(config["n_parallel"])
            self.context_length_input.setValue(config["context_length"])

            # 计算实际显存使用
            memory_usage = calculator.calculate_memory_requirements(
                config["context_length"]
            )

            UiInfoBarSuccess(
                self,
                f"已自动配置: context={config['context_length']}, "
                f"np={config['n_parallel']}, \n"
                f"当前显存占用: {total_memory_gib - available_memory_gib:.2f} GiB, \n"
                f"预计模型显存占用: {memory_usage['total_size_gib']:.2f} GiB（可能偏大）。 ",
            )

        except ValueError as e:
            UiInfoBarWarning(self, str(e))

    def save_preset(self):
        preset_name = self.config_preset_combo.currentText()
        if not preset_name:
            MessageBox("错误", "预设名称不能为空", self).exec()
            return

        selected_gpu = self.gpu_combo.currentText()
        # 如果是带有PCI ID的显示名称，保存完整的显示名称
        SETTING.set_preset(
            preset_name,
            {
                "custom_command": self.command_template.toPlainText(),
                "gpu_layers": self.gpu_layers_spinbox.value(),
                "flash_attention": self.flash_attention_check.isChecked(),
                "no_mmap": self.no_mmap_check.isChecked(),
                "gpu": selected_gpu,  # 保存完整的GPU显示名称
                "model_path": self.get_selected_model_path(),
                "context_length": self.context_length_input.value(),
                "n_parallel": self.n_parallel_spinbox.value(),
                "host": self.host_input.text(),
                "port": self.port_input.text(),
                "npp": self.npp_input.text(),
                "ntg": self.ntg_input.text(),
                "npl": self.npl_input.text(),
                "llamacpp_override": self.llamacpp_override.text(),
            },
        )
        UiInfoBarSuccess(self, "预设已保存")

    def load_presets(self, presets):
        current_preset_name = self.config_preset_combo.currentText()

        self.config_preset_combo.clear()
        preset_names = [preset["name"] for preset in presets]
        self.config_preset_combo.addItems(preset_names)

        if current_preset_name not in preset_names:
            self.config_preset_combo.setCurrentText("")
        else:
            self.config_preset_combo.setCurrentText(current_preset_name)

    def load_selected_preset(self):
        preset_name = self.config_preset_combo.currentText()
        for preset in SETTING.presets:
            if preset["name"] == preset_name:
                config = preset["config"]

                self.command_template.setPlainText(config.get("command_template", ""))
                if self.command_template == "":
                    cmd1 = config.get("custom_command", "")
                    cmd2 = config.get("custom_command_append", "")
                    if cmd1 != "":
                        self.command_template = "%cmd_raw% " + cmd1
                    elif cmd2 != "":
                        self.command_template = "%cmd% " + cmd2

                self.gpu_layers_spinbox.setValue(config.get("gpu_layers", 200))
                self.set_selected_model_path(config.get("model_path", ""))
                self.context_length_input.setValue(config.get("context_length", 2048))
                self.n_parallel_spinbox.setValue(config.get("n_parallel", 1))
                self.host_input.setText(config.get("host", "127.0.0.1"))
                self.port_input.setText(config.get("port", "8080"))
                self.flash_attention_check.setChecked(
                    config.get("flash_attention", True)
                )
                self.npp_input.setText(config.get("npp", "768"))
                self.ntg_input.setText(config.get("ntg", "384"))
                self.npl_input.setText(config.get("npl", "1,2,4,8,16"))
                self.no_mmap_check.setChecked(config.get("no_mmap", True))

                # 加载GPU选择，支持新旧格式
                gpu_setting = config.get("gpu", "")
                if gpu_setting:
                    index = self.gpu_combo.findText(gpu_setting)
                    if index >= 0:
                        self.gpu_combo.setCurrentIndex(index)
                    else:
                        # 如果找不到完整的显示名称，尝试在当前GPU列表中查找匹配的名称部分
                        from src.gpu import GPUDisplayHelper
                        for i in range(self.gpu_combo.count()):
                            current_text = self.gpu_combo.itemText(i)
                            if GPUDisplayHelper.match_gpu_name(current_text, gpu_setting):
                                self.gpu_combo.setCurrentIndex(i)
                                break

                self.llamacpp_override.setText(config.get("llamacpp_override", ""))
                self.update_context_per_thread()
                break

    def toggle_advanced_settings(self):
        new_state = not self.menu_advance.isVisible()
        self.menu_advance.setVisible(new_state)
        if SETTING.remember_advanced_state:
            SETTING.advanced_state = new_state
            SETTING.save_settings()
