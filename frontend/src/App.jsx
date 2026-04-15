import React, { useState } from 'react';
import { FilePond } from 'react-filepond';
import 'filepond/dist/filepond.min.css';

function App() {
  // State to store the URL of the processed image
  const [resultImage, setResultImage] = useState(null);

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <h1 style={{ paddingBottom: 5 }}>Analiziraj:</h1>

      <FilePond
        acceptedFileTypes={['text/csv']}
        allowMultiple={false}
        server={{
          process: (fieldName, file, metadata, load, error, progress, abort) => {
            // We use FormData to send the file to FastAPI
            const formData = new FormData();
            formData.append('file', file, file.name);

            fetch('http://localhost:8000/detect/postCsv', {
              method: 'POST',
              body: formData,
            })
              .then((response) => {
                if (!response.ok) throw new Error('Network error');
                return response.blob(); // Get the response as a binary blob (the PNG)
              })
              .then((blob) => {
                // Create a local URL for the binary blob
                const url = URL.createObjectURL(blob);
                setResultImage(url);
                load('server-done'); // Tell FilePond upload is complete
              })
              .catch((err) => {
                console.error(err);
                error('Detection failed');
              });

            return {
              abort: () => abort(),
            };
          },
        }}
        labelIdle='Povleci (.csv) ali <span class="filepond--label-action">izberi datoteko</span>'
      />

      {/* Display the result image if it exists */}
      {resultImage && (
        <div style={{ marginTop: '30px', textAlign: 'center' }}>
          <h2>Rezultat detekcije:</h2>
          <img 
            src={resultImage} 
            alt="Anomaly Detection Result" 
            style={{ width: '100%', border: '1px solid #ccc', borderRadius: '8px' }} 
          />
          <br />
          <a href={resultImage} download="rezultat.png" style={{ display: 'inline-block', marginTop: '10px' }}>
            Prenesi sliko
          </a>
        </div>
      )}
    </div>
  );
}

export default App;