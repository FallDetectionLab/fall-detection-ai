import { useState } from "react";

import WindowSize from "../hooks/windowSize";

import MetaBtn from "./SVG-MetaBtn";
import InstagramBtn from "./SVG-InstagramBtn";
import YoutubeBtn from "./SVG-YoutubeBtn";

import "./Footer.css";

function Footer() {
  const { width, height } = WindowSize();

  return (
    <footer>
      <div className="FooterSection">
        <div className="footerLeft">
          {width > 720 ? (
            <div className="copyright copyright001">
              <p>
                회사소개<span className="sliceline"></span>
              </p>
              <p>
                이용약관<span className="sliceline"></span>
              </p>
              <p>
                개인정보처리방침<span className="sliceline"></span>
              </p>
              <p>
                이메일무단수집거부<span className="sliceline"></span>
              </p>
              <p>영상정보처리기기 운영 및 관리방침</p>
            </div>
          ) : (
            <div className="copyright copyright005">
              <p>
                회사소개<span className="sliceline"></span>
              </p>
              <p>
                이용약관<span className="sliceline"></span>
              </p>
              <p>개인정보처리방침</p>
            </div>
          )}
          {width > 720 ? (
            <div className="copyright copyright002">
              <p>
                [21417] 인천광역시 부평구 무네미로 448번길 56
                <span className="sliceline"></span>
              </p>
              <p>고객센터 1544-0000 (유료) </p>
            </div>
          ) : (
            <div className="copyright copyright006">
              <p>
                이메일무단수집거부<span className="sliceline"></span>
              </p>
              <p>영상정보처리기기 운영 및 관리방침</p>
            </div>
          )}
          {width > 720 ? (
            <div className="copyright copyright003">
              <p>
                대표이사 이동민<span className="sliceline"></span>
              </p>
              <p>
                사업자등록번호 000-00-00000<span className="sliceline"></span>
              </p>
              <p>
                통신판매업신고번호 제0000호<span className="sliceline"></span>
              </p>
              <p>개인정보 보호 책임자 박상정</p>
            </div>
          ) : (
            <div className="copyright copyright007">
              <p>
                [21417] 인천광역시 부평구 무네미로 448번길 56
                <span className="sliceline"></span>
              </p>
              <p>고객센터 1544-0000 (유료) </p>
            </div>
          )}
          {width > 720 ? (
            <div className="copyright copyright004">
              <p>COPYRIGHT 2010 BY KOREA POLYTECHNICS. ALL RIGHTS RESERVED.c</p>
            </div>
          ) : (
            <div className="copyright copyright008">
              <p>
                대표이사 이동민<span className="sliceline"></span>
              </p>
              <p>사업자등록번호 000-00-00000</p>
            </div>
          )}
          {width > 720 ? (
            <div className="copyright unkown"></div>
          ) : (
            <div className="copyright copyright009">
              <p>
                통신판매업신고번호 제0000호
                <span className="sliceline"></span>
              </p>
              <p>개인정보 보호 책임자 박상정</p>
            </div>
          )}
          {width > 720 ? (
            <div className="copyright unkown"></div>
          ) : (
            <div className="copyright copyright010">
              <p>COPYRIGHT 2010 BY KOREA POLYTECHNICS. ALL RIGHTS RESERVED.c</p>
            </div>
          )}
        </div>
        <div className="footerRight">
          <h3>Follow Us</h3>
          <div className="footerBtnBox">
            <YoutubeBtn />
            <InstagramBtn />
            <MetaBtn />
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
