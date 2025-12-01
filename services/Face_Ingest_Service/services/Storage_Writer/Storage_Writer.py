from src.Storage_Writer import StorageWriter
def main():
    storage_writer = StorageWriter()
    client_data = {
        "file_name": "example.txt",
        "content": b"Hello, World!"
    }
    destination = "./test_storage"
    success = storage_writer.write_data(client_data, destination)
    if success:
        print("Data written successfully.")
    else:
        print("Failed to write data.")
    