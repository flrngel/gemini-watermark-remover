from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from .processors.image import SUPPORTED_IMAGE_FORMATS, is_supported_image, process_image
from .processors.video import SUPPORTED_VIDEO_FORMATS, is_supported_video, process_video

app = typer.Typer(
    name="gwr",
    help="Remove AI watermarks (Gemini + Veo) from images and videos.",
    add_completion=True,
)
console = Console()


def get_files_to_process(path: Path, recursive: bool = False) -> list[Path]:
    """Get all supported files from path (file or directory)."""
    if path.is_file():
        return [path]

    files = []
    pattern = "**/*" if recursive else "*"

    for f in path.glob(pattern):
        if f.is_file() and (is_supported_image(f) or is_supported_video(f)):
            files.append(f)

    return sorted(files)


@app.command()
def process(
    path: Path = typer.Argument(
        ...,
        help="Path to image/video file or directory for batch processing",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (file or directory). Defaults to input location with '_output' suffix.",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Process directories recursively",
    ),
    suffix: str = typer.Option(
        "_output",
        "--suffix",
        "-s",
        help="Suffix to add to output filenames",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        "-y",
        help="Overwrite existing output files without prompting",
    ),
):
    """
    Remove all AI watermarks from images and videos.

    Automatically removes both Gemini and Veo watermarks.
    Videos are output as MP4 with H.264 encoding.

    Examples:
        gwr process image.png
        gwr process video.mp4 -o cleaned_video.mp4
        gwr process ./photos/ -r --suffix "_nowatermark"
    """
    files = get_files_to_process(path, recursive)

    if not files:
        console.print(f"[red]No supported files found in {path}[/red]")
        console.print(f"Supported formats: {SUPPORTED_IMAGE_FORMATS | SUPPORTED_VIDEO_FORMATS}")
        raise typer.Exit(1)

    # Determine output directory for batch processing
    output_dir = None
    if path.is_dir() and output:
        output_dir = output
        output_dir.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel(
            f"Processing {len(files)} file(s) (removing Gemini + Veo watermarks)",
            title="AI Watermark Remover",
            border_style="blue",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        main_task = progress.add_task("Processing files...", total=len(files))

        for file_path in files:
            progress.update(main_task, description=f"Processing {file_path.name}...")

            # Determine output path for this file
            if output_dir:
                file_output = (
                    output_dir
                    / f"{file_path.stem}{suffix}{'.mp4' if is_supported_video(file_path) else '.png'}"
                )
            elif output and path.is_file():
                file_output = output
            else:
                file_output = None  # Use default naming

            # Check for overwrite
            if file_output and file_output.exists() and not overwrite:
                if not typer.confirm(f"Overwrite {file_output}?"):
                    progress.advance(main_task)
                    continue

            try:
                if is_supported_image(file_path):
                    result = process_image(file_path, file_output, suffix)
                    console.print(f"  [green]Image saved:[/green] {result}")

                elif is_supported_video(file_path):
                    frame_task = progress.add_task("  Frames...", total=100, visible=True)

                    def video_progress(current: int, total: int):
                        progress.update(frame_task, completed=int(current / total * 100))

                    result = process_video(file_path, file_output, suffix, video_progress)
                    progress.remove_task(frame_task)
                    console.print(f"  [green]Video saved:[/green] {result}")

            except Exception as e:
                console.print(f"  [red]Error processing {file_path}:[/red] {e}")

            progress.advance(main_task)

    console.print("[bold green]Done![/bold green]")


@app.command()
def info():
    """Display information about supported formats and algorithm."""
    console.print(
        Panel(
            "[bold]AI Watermark Remover[/bold]\n\n"
            "Removes all watermarks from Google AI-generated images and videos.\n"
            "Both Gemini and Veo watermarks are removed automatically.\n\n"
            "[cyan]Watermarks Removed:[/cyan]\n"
            "  - Gemini sparkle logo (bottom-right, alpha blending)\n"
            "  - Veo text watermark (bottom-right, delogo filter)\n\n"
            f"[cyan]Supported Image Formats:[/cyan] {', '.join(sorted(SUPPORTED_IMAGE_FORMATS))}\n"
            f"[cyan]Supported Video Formats:[/cyan] {', '.join(sorted(SUPPORTED_VIDEO_FORMATS))}\n"
            "[cyan]Video Output:[/cyan] MP4 (H.264)\n\n"
            "[dim]Gemini: reverse alpha blending with known alpha map[/dim]\n"
            "[dim]Veo: ffmpeg delogo spatial interpolation[/dim]",
            title="About",
            border_style="blue",
        )
    )


if __name__ == "__main__":
    app()
