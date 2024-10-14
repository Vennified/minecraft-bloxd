document.addEventListener('DOMContentLoaded', function () {
    const uploadFileBox = document.getElementById('uploadfile');
    const fileInput = document.getElementById('fileInput');
    const downloadLink = document.getElementById('downloadLink');
    const downloadButton = document.getElementById('downloadButton');
    const resourcePackText = document.querySelector('.resource-pack-text');
    const centerIcon = document.querySelector('.center-icon');
    const uploadFilesText = document.querySelector('.upload-files-text');

    uploadFileBox.addEventListener('click', function () {
        fileInput.click();
    });

    // Add this function to your JavaScript
    async function uploadToCloudinary(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('upload_preset', 'your_unsigned_upload_preset'); // Replace with your actual Cloudinary preset

        const response = await fetch('https://api.cloudinary.com/v1_1/your_cloud_name/raw/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    fileInput.addEventListener('change', async function (event) {
        const file = event.target.files[0];
        if (file) {
            resourcePackText.style.display = 'none';
            centerIcon.style.display = 'none';
            downloadLink.style.display = 'none';
            downloadButton.style.display = 'none';

            uploadFilesText.textContent = 'Uploading...';

            try {
                // Step 1: Upload to Cloudinary
                const cloudinaryResponse = await uploadToCloudinary(file);

                // Step 2: Send the Cloudinary URL to your server for processing
                const serverResponse = await fetch("/process", {
                    method: "POST",
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ cloudinary_url: cloudinaryResponse.secure_url })
                });

                if (!serverResponse.ok) {
                    throw new Error(`HTTP error! status: ${serverResponse.status}`);
                }

                const data = await serverResponse.json();

                // Step 3: If the server responds with a download URL, update the UI
                if (data.download_url) {
                    downloadLink.href = data.download_url;
                    downloadLink.style.display = 'block';
                    downloadButton.style.display = 'block';

                    uploadFilesText.textContent = 'Download Zip File';
                } else {
                    console.error('No download URL received in the server response');
                }
            } catch (error) {
                console.error('Error:', error);
                alert(`Error: ${error.message}`);
            }
        }
    });
});
