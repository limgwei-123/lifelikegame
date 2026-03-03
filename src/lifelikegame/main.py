from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def main():
  return {"app":"lifelikegame"}

@app.get("/healthy")
def healthy():
  return {"status":"Ok"}

# def main():
#     print("Hello from lifelikegame!")


# if __name__ == "__main__":
#     main()
