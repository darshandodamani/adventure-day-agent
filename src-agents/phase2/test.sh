URL="https://phase2.orangeforest-49a035fa.swedencentral.azurecontainerapps.io"

curl -X 'POST' \
  "$URL/ask" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "question": "Which of the options below is a correct genre for the movie The Smoorgh Crusade? Action, Drama, Comedy, Adventure",
  "type": "multiple_choice",
  "correlationToken": "1234567890"
}'

curl -X 'POST' \
  "$URL/ask" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "question": "Does The Lost City have any sequels planned? True or False",
  "type": "true_or_false",
  "correlationToken": "1234567890"
}'