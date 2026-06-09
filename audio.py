"""WASAPI Loopback 音频捕获 + FFT 频率分析"""
import threading, time, math
import numpy as np

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    pyaudio = None


class AudioCapture:
    """实时系统音频捕获，提供 FFT 频带数据"""

    def __init__(self, num_bands: int = 80, fft_size: int = 2048,
                 sensitivity: float = 1.0, smoothing: float = 0.3):
        self.num_bands = int(num_bands)
        self.fft_size = int(fft_size)
        self.sensitivity = sensitivity
        self.smoothing = smoothing

        self.fft_bands = np.zeros(num_bands, dtype=np.float32)
        self.energy = 0.0
        self.peak = 0.0
        self.dominant_freq = 0.0  # 主频 Hz
        self.enabled = False

        self._lock = threading.Lock()
        self._thread = None
        self._stop = False
        self._raw_spectrum = np.zeros(fft_size // 2, dtype=np.float32)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self.enabled = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        self.enabled = False

    def get_data(self):
        """返回 (fft_bands, energy, peak, dominant_freq)"""
        with self._lock:
            return (self.fft_bands.copy(), self.energy,
                    self.peak, self.dominant_freq)

    def update_params(self, num_bands=None, sensitivity=None,
                      smoothing=None, fft_size=None):
        if num_bands is not None:
            self.num_bands = int(num_bands)
        if sensitivity is not None:
            self.sensitivity = sensitivity
        if smoothing is not None:
            self.smoothing = smoothing
        if fft_size is not None and int(fft_size) != self.fft_size:
            self.fft_size = int(fft_size)

    def _run(self):
        if pyaudio is None:
            print("[Audio] pyaudiowpatch 未安装")
            self.enabled = False
            return

        p = pyaudio.PyAudio()
        try:
            wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except Exception as e:
            print(f"[Audio] WASAPI 不可用: {e}")
            self.enabled = False
            p.terminate()
            return

        # 找 loopback 设备（匹配默认扬声器）
        loopback = None
        default_idx = wasapi['defaultOutputDevice']
        speaker = p.get_device_info_by_index(default_idx)
        speaker_name = speaker['name']
        print(f"[Audio] 默认扬声器: {speaker_name}")

        for i in range(p.get_device_count()):
            d = p.get_device_info_by_index(i)
            if d.get('isLoopbackDevice', False) and d['hostApi'] == wasapi['index']:
                if speaker_name in d['name']:
                    loopback = d
                    break
        if loopback is None:
            # fallback: 找任意 loopback
            for i in range(p.get_device_count()):
                d = p.get_device_info_by_index(i)
                if d.get('isLoopbackDevice', False) and d['hostApi'] == wasapi['index']:
                    loopback = d
                    break

        if loopback is None:
            print("[Audio] 找不到 loopback 设备")
            self.enabled = False
            p.terminate()
            return

        sample_rate = int(loopback['defaultSampleRate'])
        channels = int(loopback['maxInputChannels'])
        frames = self.fft_size
        print(f"[Audio] 设备: {loopback['name']}, 采样率: {sample_rate}, 声道: {channels}")

        # 预计算频率映射：对数分布，低频密、高频疏
        freq_bins = self.fft_size // 2
        bin_hz = sample_rate / self.fft_size
        self._band_edges = self._make_band_edges(
            self.num_bands, freq_bins, bin_hz)

        window = np.hanning(self.fft_size)
        buffer = np.zeros(self.fft_size, dtype=np.float32)
        buf_pos = 0
        _debug_count = 0

        def callback(in_data, frame_count, time_info, status):
            nonlocal buffer, buf_pos, _debug_count
            if self._stop:
                return (None, pyaudio.paComplete)

            data = np.frombuffer(in_data, dtype=np.float32)
            # 多声道取均值
            if channels > 1:
                data = data.reshape(-1, channels).mean(axis=1)

            _debug_count += 1

            # 填充环形缓冲
            remaining = len(data)
            src_pos = 0
            while remaining > 0:
                space = self.fft_size - buf_pos
                chunk = min(remaining, space)
                buffer[buf_pos:buf_pos + chunk] = data[src_pos:src_pos + chunk]
                buf_pos += chunk
                src_pos += chunk
                remaining -= chunk

                if buf_pos >= self.fft_size:
                    self._process_fft(buffer, window, sample_rate)
                    buf_pos = 0

            return (None, pyaudio.paContinue)

        try:
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=loopback['index'],
                frames_per_buffer=frames,
                stream_callback=callback,
            )
            stream.start_stream()
            while not self._stop and stream.is_active():
                time.sleep(0.05)
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"[Audio] 流失败: {e}")
        finally:
            p.terminate()
        self.enabled = False

    def _make_band_edges(self, num_bands, freq_bins, bin_hz):
        """对数频率映射：20Hz ~ 20kHz 分成 num_bands 段"""
        min_freq = 20.0
        max_freq = min(20000.0, freq_bins * bin_hz)
        log_min = math.log10(min_freq)
        log_max = math.log10(max_freq)

        edges = []
        for i in range(num_bands + 1):
            ratio = i / num_bands
            freq = 10 ** (log_min + ratio * (log_max - log_min))
            bin_idx = int(freq / bin_hz)
            edges.append(min(bin_idx, freq_bins - 1))
        return edges

    def _process_fft(self, buffer, window, sample_rate):
        """FFT → 频带能量"""
        windowed = buffer * window
        spectrum = np.abs(np.fft.rfft(windowed))[:-1]
        spectrum = spectrum / (self.fft_size / 2)

        # 映射到频带
        bands = np.zeros(self.num_bands, dtype=np.float32)
        for i in range(self.num_bands):
            lo = self._band_edges[i]
            hi = self._band_edges[i + 1]
            if hi > lo:
                bands[i] = np.mean(spectrum[lo:hi])

        # 灵敏度 + 压缩
        bands = np.clip(bands * self.sensitivity * 5.0, 0.0, 1.0)
        bands = np.power(bands, 0.6)  # gamma 压缩，让小值更明显

        # RMS 能量
        rms = float(np.sqrt(np.mean(buffer ** 2)))
        energy = min(1.0, rms * self.sensitivity * 5.0)

        # 主频
        peak_bin = int(np.argmax(spectrum))
        dominant_freq = peak_bin * sample_rate / self.fft_size

        # 平滑
        s = self.smoothing
        with self._lock:
            self.fft_bands = self.fft_bands * s + bands * (1.0 - s)
            self.energy = self.energy * s + energy * (1.0 - s)
            self.peak = max(self.peak * 0.95, self.energy)
            self.dominant_freq = dominant_freq
            self._raw_spectrum = spectrum


