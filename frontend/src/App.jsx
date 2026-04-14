import { FilePond, registerPlugin } from 'react-filepond'
import 'filepond/dist/filepond.min.css'

function App() {
  return (
    <>
      <h1 style={{paddingBottom:5}}>Analiziraj:</h1>

      <FilePond
        acceptedFileTypes={['text/csv/zip']}
        allowMultiple={false}
        server={{
          process: {
            url: 'http://localhost:3000/upload',  
            method: 'POST',
            onload: (response) => {
              console.log('Success:', response)
            },
            onerror: (response) => {
              console.log('Error:', response)
            },
          }
        }}
        labelIdle='Povleci (.csv .zip) ali <span class="filepond--label-action">izberi datoteko</span>'
      />
    </>
  )
}
export default App
