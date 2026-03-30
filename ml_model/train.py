"""
AIoT Smart Waste Management System
===================================
Plastic Waste Classification Model Training
Uses transfer learning with MobileNetV2 to classify plastic waste
into Recyclable and Non-Recyclable categories.

Dataset: Collect images of recyclable and non-recyclable plastic waste
Folder structure:
    dataset/
        train/
            Recyclable/   (plastic bottles, clean containers, etc.)
            NonRecyclable/ (contaminated plastic, multi-layer packaging, etc.)
        val/
            Recyclable/
            NonRecyclable/
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
import matplotlib.pyplot as plt
import json

# ─── Config ──────────────────────────────────────────────────────────────────
DATASET_DIR = "dataset"
MODEL_SAVE_PATH = "waste_classifier.pt"
CLASSES = ["NonRecyclable", "Recyclable"]
IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 15
LR = 0.001
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ─── Data Transforms ─────────────────────────────────────────────────────────
train_transforms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

val_transforms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


def load_data():
    train_ds = datasets.ImageFolder(os.path.join(DATASET_DIR, "train"), train_transforms)
    val_ds   = datasets.ImageFolder(os.path.join(DATASET_DIR, "val"),   val_transforms)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=2)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=2)
    print(f"Classes: {train_ds.classes}")
    print(f"Train: {len(train_ds)} | Val: {len(val_ds)}")
    return train_loader, val_loader, train_ds.classes


def build_model(num_classes=2):
    """MobileNetV2 with custom classifier head — lightweight, fast on edge devices."""
    model = models.mobilenet_v2(pretrained=True)
    # Freeze backbone
    for param in model.features.parameters():
        param.requires_grad = False
    # Replace classifier
    model.classifier = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(model.last_channel, 128),
        nn.ReLU(),
        nn.Linear(128, num_classes),
    )
    return model.to(DEVICE)


def train_one_epoch(model, loader, criterion, optimizer):
    model.train()
    total_loss, correct = 0.0, 0
    for images, labels in loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * images.size(0)
        correct += (outputs.argmax(1) == labels).sum().item()
    n = len(loader.dataset)
    return total_loss / n, correct / n


def evaluate(model, loader, criterion):
    model.eval()
    total_loss, correct = 0.0, 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            total_loss += criterion(outputs, labels).item() * images.size(0)
            correct += (outputs.argmax(1) == labels).sum().item()
    n = len(loader.dataset)
    return total_loss / n, correct / n


def main():
    train_loader, val_loader, classes = load_data()
    model = build_model(num_classes=len(classes))
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.classifier.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    best_val_acc = 0.0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    print(f"\nTraining on {DEVICE}")
    print("=" * 55)

    for epoch in range(1, EPOCHS + 1):
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer)
        vl_loss, vl_acc = evaluate(model, val_loader, criterion)
        scheduler.step()

        history["train_loss"].append(tr_loss)
        history["train_acc"].append(tr_acc)
        history["val_loss"].append(vl_loss)
        history["val_acc"].append(vl_acc)

        print(f"Epoch {epoch:02d}/{EPOCHS} | "
              f"Train Loss: {tr_loss:.4f} Acc: {tr_acc:.4f} | "
              f"Val Loss: {vl_loss:.4f} Acc: {vl_acc:.4f}")

        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            torch.save({
                "model_state": model.state_dict(),
                "classes": classes,
                "img_size": IMG_SIZE,
            }, MODEL_SAVE_PATH)
            print(f"  ✓ Saved best model (val_acc={vl_acc:.4f})")

    print(f"\nBest Val Accuracy: {best_val_acc:.4f}")

    # Save class mapping
    with open("class_mapping.json", "w") as f:
        json.dump({i: c for i, c in enumerate(classes)}, f)

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(history["train_loss"], label="Train")
    ax1.plot(history["val_loss"],   label="Val")
    ax1.set_title("Loss"); ax1.legend()
    ax2.plot(history["train_acc"], label="Train")
    ax2.plot(history["val_acc"],   label="Val")
    ax2.set_title("Accuracy"); ax2.legend()
    plt.tight_layout()
    plt.savefig("training_history.png")
    print("Training plot saved to training_history.png")


if __name__ == "__main__":
    main()
