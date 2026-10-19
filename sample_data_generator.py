import os
import datetime
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

def create_synthetic_dicom_dataset(
    filename: str,
    patient_id: str,
    patient_name: str,
    study_uid: str,
    series_uid: str,
    sop_uid: str,
    modality: str,
    study_desc: str,
    series_desc: str,
    study_date: datetime.date,
    instance_num: int,
    total_instances: int
):
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Populate required DICOM header metadata
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage if modality == 'CT' else pydicom.uid.MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)

    ds.PatientID = patient_id
    ds.PatientName = patient_name
    ds.PatientSex = "M" if hash(patient_id) % 2 == 0 else "F"
    ds.PatientBirthDate = "19800101"

    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.SOPInstanceUID = sop_uid
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID

    ds.Modality = modality
    ds.StudyDescription = study_desc
    ds.SeriesDescription = series_desc
    ds.StudyDate = study_date.strftime("%Y%m%d")
    ds.StudyTime = "120000"
    ds.AccessionNumber = f"ACC-{hash(study_uid) % 1000000:06d}"

    ds.InstanceNumber = instance_num
    ds.SeriesNumber = 1
    ds.SliceLocation = float(instance_num * 2.5)

    # Pixel Data Specs
    rows, cols = 128, 128
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"

    # Generate synthetic image geometry (e.g. cross section of anatomy changing with slice)
    y, x = np.ogrid[:rows, :cols]
    center_y, center_x = rows // 2, cols // 2

    # Radius shrinks/grows across instances to simulate 3D volume slicing
    factor = np.sin(np.pi * (instance_num / max(1, total_instances)))
    radius = (rows // 3) * factor + 5

    dist_from_center = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    mask = dist_from_center <= radius

    arr = np.zeros((rows, cols), dtype=np.uint16)
    # Bright center with gradient ring
    arr[mask] = (2000 * (1 - dist_from_center[mask] / radius)).astype(np.uint16) + 400

    # Add anatomical structures (inner circle or bone ring for CT)
    if modality == 'CT':
        inner_mask = dist_from_center <= (radius * 0.4)
        arr[inner_mask] = 1200  # CT bone/contrast level
    elif modality == 'MR':
        inner_mask = (dist_from_center <= (radius * 0.7)) & (dist_from_center >= (radius * 0.3))
        arr[inner_mask] = 1800  # MR brain matter signal

    ds.PixelData = arr.tobytes()
    ds.save_as(filename, write_like_original=False)


def generate_sample_dicom_dataset(output_dir: str = "sample_dicom_data") -> str:
    """Generates a rich multi-modality DICOM study dataset for testing and demoing."""
    today = datetime.date.today()
    studies_info = [
        {
            "patient_id": "PAT-001",
            "patient_name": "Doe^John",
            "study_desc": "CT Chest Scan with Contrast",
            "modality": "CT",
            "study_date": today - datetime.timedelta(days=2),
            "series_count": 2,
            "slices_per_series": 8,
        },
        {
            "patient_id": "PAT-002",
            "patient_name": "Smith^Alice",
            "study_desc": "MRI Brain Examination",
            "modality": "MR",
            "study_date": today - datetime.timedelta(days=5),
            "series_count": 1,
            "slices_per_series": 10,
        },
        {
            "patient_id": "PAT-003",
            "patient_name": "Wayne^Bruce",
            "study_desc": "Chest X-Ray AP/Lateral",
            "modality": "CR",
            "study_date": today - datetime.timedelta(days=15),
            "series_count": 1,
            "slices_per_series": 2,
        },
        {
            "patient_id": "PAT-004",
            "patient_name": "Stark^Tony",
            "study_desc": "CT Abdomen Pelvis",
            "modality": "CT",
            "study_date": today - datetime.timedelta(days=30),
            "series_count": 1,
            "slices_per_series": 6,
        },
        {
            "patient_id": "PAT-005",
            "patient_name": "Parker^Peter",
            "study_desc": "Ultrasound Abdomen",
            "modality": "US",
            "study_date": today - datetime.timedelta(days=1),
            "series_count": 1,
            "slices_per_series": 5,
        }
    ]

    for s_idx, st in enumerate(studies_info):
        study_uid = f"1.2.840.10008.5.1.4.1.1.2.{s_idx + 1}"
        for ser_idx in range(st["series_count"]):
            series_uid = f"{study_uid}.{ser_idx + 1}"
            series_desc = f"{st['modality']} Series {ser_idx + 1}"
            num_slices = st["slices_per_series"]
            for i in range(1, num_slices + 1):
                sop_uid = f"{series_uid}.{i}"
                filename = os.path.join(
                    output_dir,
                    f"study_{s_idx+1}",
                    f"series_{ser_idx+1}",
                    f"slice_{i:03d}.dcm"
                )
                create_synthetic_dicom_dataset(
                    filename=filename,
                    patient_id=st["patient_id"],
                    patient_name=st["patient_name"],
                    study_uid=study_uid,
                    series_uid=series_uid,
                    sop_uid=sop_uid,
                    modality=st["modality"],
                    study_desc=st["study_desc"],
                    series_desc=series_desc,
                    study_date=st["study_date"],
                    instance_num=i,
                    total_instances=num_slices
                )

    return output_dir

if __name__ == "__main__":
    out = generate_sample_dicom_dataset()
    print(f"Generated sample DICOM dataset in '{out}'")
