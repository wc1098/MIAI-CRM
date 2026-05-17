import axios from "axios";

import CommonUploadAPI, { type UploadConfirmResponse, type UploadScene } from "@/api/module_common/upload";
import ParamsAPI from "@/api/module_system/params";

const IMAGE_MAX_SIDE = 1600;
const IMAGE_QUALITY = 0.82;

function isImage(file: File) {
  return file.type.startsWith("image/");
}

function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality: number) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error("图片压缩失败"));
      },
      type === "image/png" ? "image/jpeg" : type,
      quality
    );
  });
}

async function compressImage(file: File) {
  if (!isImage(file)) return file;
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, IMAGE_MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  if (scale >= 1 && file.size <= 4 * 1024 * 1024) return file;
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  const ctx = canvas.getContext("2d");
  if (!ctx) return file;
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const contentType = file.type === "image/png" ? "image/jpeg" : file.type || "image/jpeg";
  const blob = await canvasToBlob(canvas, contentType, IMAGE_QUALITY);
  const ext = contentType === "image/webp" ? "webp" : "jpg";
  const filename = file.name.replace(/\.[^.]+$/, `.${ext}`);
  return new File([blob], filename, { type: contentType, lastModified: Date.now() });
}

async function fallbackUpload(file: File): Promise<UploadConfirmResponse> {
  const body = new FormData();
  body.append("file", file);
  const res = await ParamsAPI.uploadFile(body);
  const data = res.data.data;
  return {
    file_name: data.file_name || file.name,
    origin_name: data.origin_name || file.name,
    file_path: data.file_path || "",
    file_url: data.file_url,
    object_key: data.file_path || "",
    scene: "common_image",
  };
}

export async function uploadImageDirect(file: File, scene: UploadScene): Promise<UploadConfirmResponse> {
  if (!isImage(file)) return fallbackUpload(file);
  const compressed = await compressImage(file);
  try {
    const policyRes = await CommonUploadAPI.ossPolicy({
      scene,
      filename: compressed.name,
      content_type: compressed.type || "image/jpeg",
      size: compressed.size,
    });
    const policy = policyRes.data.data;
    const formData = new FormData();
    formData.append("key", policy.object_key);
    formData.append("policy", policy.policy);
    formData.append("OSSAccessKeyId", policy.access_key_id);
    formData.append("Signature", policy.signature);
    formData.append("success_action_status", "200");
    formData.append("Content-Type", compressed.type || "image/jpeg");
    formData.append("file", compressed);
    await axios.post(policy.host, formData, { headers: { "Content-Type": "multipart/form-data" } });
    const confirmRes = await CommonUploadAPI.confirm({
      scene,
      object_key: policy.object_key,
      file_url: policy.file_url,
    });
    return confirmRes.data.data;
  } catch (error) {
    console.warn("OSS直传失败，回退后端上传", error);
    return fallbackUpload(compressed);
  }
}
