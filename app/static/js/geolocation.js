// ============================================================
// Roll Call Geolocation
// ============================================================

function getCurrentPosition() {

  return new Promise((resolve, reject) => {

    // Browser does not support geolocation
    if (!navigator.geolocation) {

      reject(
        new Error(
          "Geolocation is not supported by this browser."
        )
      );

      return;
    }


    console.log(
      "Requesting browser location permission..."
    );


    navigator.geolocation.getCurrentPosition(

      // --------------------------------------------------------
      // SUCCESS
      // --------------------------------------------------------

      (position) => {

        console.log(
          "Location permission granted."
        );

        console.log(
          "Latitude:",
          position.coords.latitude
        );

        console.log(
          "Longitude:",
          position.coords.longitude
        );

        console.log(
          "Accuracy:",
          position.coords.accuracy,
          "meters"
        );

        resolve(position);
      },


      // --------------------------------------------------------
      // ERROR
      // --------------------------------------------------------

      (error) => {

        console.error(
          "Geolocation error:",
          error
        );


        let message;


        switch (error.code) {

          case error.PERMISSION_DENIED:

            message =
              "Location permission was denied.";

            break;


          case error.POSITION_UNAVAILABLE:

            message =
              "Your location is currently unavailable.";

            break;


          case error.TIMEOUT:

            message =
              "Location request timed out.";

            break;


          default:

            message =
              "Unable to get your location.";
        }


        reject(
          new Error(message)
        );
      },


      // --------------------------------------------------------
      // OPTIONS
      // --------------------------------------------------------

      {
        enableHighAccuracy: true,

        timeout: 15000,

        maximumAge: 0
      }

    );

  });

}