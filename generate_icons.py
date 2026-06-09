"""用 ComfyUI API 生成音乐可视化器图标"""
import json, time, urllib.request, urllib.error, os, struct, zlib

COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# 3 个图标的 prompt
ICONS = [
    {
        "name": "music_visualizer",
        "prompt": "a minimal flat icon of audio spectrum bars with rainbow gradient colors, glowing, dark background, centered, 128x128, clean design, no text",
    },
    {
        "name": "aura_light",
        "prompt": "a minimal flat icon of a soft glowing aura light effect, cyan and blue gradient, ambient glow, dark background, centered, 128x128, clean design, no text",
    },
    {
        "name": "edge_glow",
        "prompt": "a minimal flat icon of a bottom edge light strip, neon glow effect, purple to blue gradient, dark background, centered, 128x128, clean design, no text",
    },
]


def make_workflow(prompt_text):
    """构建 FLUX.1 schnell 的工作流"""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(time.time() * 1000) % (2**32),
                "steps": 4,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": "flux1-schnell-Q4_K_S.gguf"},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 128, "height": 128, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_text, "clip": ["8", 0]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "text, watermark, blurry, low quality", "clip": ["8", 0]},
        },
        "8": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5xxl_fp8_e4m3fn.safetensors",
                "type": "flux",
            },
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["10", 0]},
        },
        "10": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"},
        },
        "11": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "icon", "images": ["9", 0]},
        },
    }


def queue_prompt(workflow):
    """提交工作流到 ComfyUI"""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_history(prompt_id):
    """获取生成历史"""
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as resp:
        return json.loads(resp.read())


def download_image(filename, subfolder, output_type="output"):
    """下载生成的图片"""
    url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type={output_type}"
    with urllib.request.urlopen(url) as resp:
        return resp.read()


def png_to_ico(png_data, ico_path, sizes=(16, 32, 48, 64, 128)):
    """将 PNG 数据转为 ICO 文件（多尺寸）"""
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(png_data))
    icons = []
    for size in sizes:
        resized = img.resize((size, size), Image.LANCZOS)
        icons.append(resized)

    # 保存为 ICO
    icons[0].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes],
                  append_images=icons[1:])


def generate_icon(icon_info):
    """生成单个图标"""
    name = icon_info["name"]
    prompt_text = icon_info["prompt"]

    print(f"[{name}] 生成中...")
    workflow = make_workflow(prompt_text)

    try:
        result = queue_prompt(workflow)
        prompt_id = result["prompt_id"]
        print(f"[{name}] 已提交: {prompt_id}")
    except Exception as e:
        print(f"[{name}] 提交失败: {e}")
        return None

    # 等待完成
    for _ in range(120):  # 最多等 2 分钟
        time.sleep(2)
        try:
            history = get_history(prompt_id)
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for img_info in node_output["images"]:
                            filename = img_info["filename"]
                            subfolder = img_info.get("subfolder", "")
                            png_data = download_image(filename, subfolder)

                            # 保存 PNG
                            png_path = os.path.join(OUTPUT_DIR, f"{name}.png")
                            with open(png_path, "wb") as f:
                                f.write(png_data)

                            # 转 ICO
                            ico_path = os.path.join(OUTPUT_DIR, f"{name}.ico")
                            png_to_ico(png_data, ico_path)

                            print(f"[{name}] 完成: {png_path} + {ico_path}")
                            return ico_path
        except Exception:
            pass

    print(f"[{name}] 超时")
    return None


if __name__ == "__main__":
    results = []
    for icon in ICONS:
        result = generate_icon(icon)
        results.append(result)

    print("\n=== 结果 ===")
    for icon, result in zip(ICONS, results):
        status = "✅" if result else "❌"
        print(f"  {status} {icon['name']}: {result}")
